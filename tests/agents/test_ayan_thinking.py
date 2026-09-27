import pytest
from pydantic import ValidationError

from backend.app.agents.ayan_thinking import (
    AyanCriticalThinkingAgent,
    AyanResponseError,
)
from backend.app.ai.mock_provider import MockAIProvider
from backend.app.schemas.ayan import (
    AyanCriticalThinkingTask,
    AyanGeneratedThinking,
)
from backend.app.schemas.mira import MiraTeachingResponse, MiraSourceReference


def _task():
    return AyanCriticalThinkingTask(
        session_id="ses_1",
        concept="Information Gain",
        learning_goal="Explain how decision trees select splits",
        learner_state="I know basic probability",
        interest="Sports analytics",
        current_level="beginner",
        mira_teaching_result=MiraTeachingResponse(
            session_id="ses_1",
            concept="Information Gain",
            explanation="It compares the usefulness of possible splits.",
            key_points=["Compare candidate splits."],
            examples=["Compare player statistics."],
            learner_level="beginner",
            teaching_style="step by step",
            source_references=[
                MiraSourceReference(
                    source_id="src_1",
                    title="Information Gain Guide",
                    url="https://example.edu/information-gain",
                )
            ],
            generated_at="2026-01-01T00:00:00Z",
        ),
        research_source_references=[
            MiraSourceReference(
                source_id="src_1",
                title="Information Gain Guide",
                url="https://example.edu/information-gain",
            )
        ],
        critical_thinking_instruction="Ask one open-ended why/how question.",
    )


def test_ayan_task_contract_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        AyanCriticalThinkingTask.model_validate(
            {"session_id": "ses_1", "manual_level": "expert"}
        )


def test_ayan_generates_reasoning_prompt_from_mira_context():
    provider = MockAIProvider()
    response = AyanCriticalThinkingAgent(provider).create_activity(_task())

    assert response.session_id == "ses_1"
    assert response.concept == "Information Gain"
    assert response.difficulty == "beginner"
    assert response.thinking_prompt
    assert response.expected_reasoning_focus
    assert [source.source_id for source in response.source_references] == ["src_1"]


@pytest.mark.parametrize(
    ("output", "message"),
    [
        (
            {
                "concept": "A different concept",
                "thinking_prompt": "Explain why.",
                "expected_reasoning_focus": ["Explain the relationship."],
                "difficulty": "beginner",
                "source_reference_ids": ["src_1"],
            },
            "does not match the concept",
        ),
        (
            {
                "concept": "Information Gain",
                "thinking_prompt": " ",
                "expected_reasoning_focus": ["Explain the relationship."],
                "difficulty": "advanced",
                "source_reference_ids": ["src_1"],
            },
            "incomplete thinking content",
        ),
        (
            {
                "concept": "Information Gain",
                "thinking_prompt": "Explain why.",
                "expected_reasoning_focus": ["Explain the relationship."],
                "difficulty": "beginner",
                "source_reference_ids": ["forged"],
            },
            "outside the supplied research context",
        ),
    ],
)
def test_ayan_rejects_unscoped_output(output, message):
    provider = MockAIProvider(
        custom_responses={AyanGeneratedThinking.__name__: output}
    )

    with pytest.raises(AyanResponseError, match=message):
        AyanCriticalThinkingAgent(provider).create_activity(_task())
