import json

import pytest
from pydantic import ValidationError

from backend.app.agents.kira import KiraPracticalAgent, KiraResponseError, KiraTask
from backend.app.ai.mock_provider import MockAIProvider
from backend.app.agents.kira.contracts import KiraGeneratedPractical


def _task():
    return KiraTask.model_validate({
        "session_id": "ses_1",
        "orchestration_id": "orch_1",
        "concept_id": "con_1",
        "concept_name": "Information Gain",
        "learning_objective": "Explain how decision trees select a split",
        "teaching_result_reference": {
            "result_id": "teach_1",
            "concept_name": "Information Gain",
            "explanation": "It compares how useful candidate splits are.",
            "key_points": ["Compare candidate splits."],
            "examples": ["Compare player statistics."],
        },
        "thinking_result_reference": {
            "result_id": "think_1",
            "concept_name": "Information Gain",
            "thinking_prompt": "Why might one split be more useful?",
            "expected_reasoning_focus": ["Explain the relationship to uncertainty."],
        },
        "research_source_ids": ["src_1"],
        "research_summary": "Information gain compares possible tree splits.",
        "research_sources": [{
            "source_id": "src_1",
            "title": "Decision Tree Guide",
            "snippet": "Information gain compares useful data splits.",
        }],
        "learner_context": {
            "task": "Understand information gain",
            "learner_state": "I know basic probability",
            "interest": "Sports analytics",
            "learner_level": "beginner",
        },
        "task_instruction": "Create a practical activity without grading.",
    })


def test_kira_task_contract_is_strict():
    task = _task().model_dump()
    task["manual_level"] = "expert"
    with pytest.raises(ValidationError):
        KiraTask.model_validate(task)


def test_kira_creates_a_practical_activity_from_supplied_context():
    provider = MockAIProvider()
    response = KiraPracticalAgent(provider).create_activity(_task())

    assert response.agent == "Kira"
    assert response.session_id == "ses_1"
    assert response.orchestration_id == "orch_1"
    assert response.concept_id == "con_1"
    assert response.scenario
    assert response.practical_task
    assert response.real_world_context
    assert response.expected_action
    assert response.success_criteria
    assert response.difficulty == "beginner"
    assert response.research_source_ids == ["src_1"]
    serialized = json.loads(provider.call_history[0]["prompt"].partition(
        "Kira practical task:\n"
    )[2])
    assert serialized["thinking_result_reference"]["result_id"] == "think_1"
    assert serialized["research_sources"][0]["source_id"] == "src_1"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {
                "scenario": "A real scenario.",
                "practical_task": "Apply the concept.",
                "real_world_context": "An application context.",
                "expected_action": "Explain your approach.",
                "success_criteria": ["Connect evidence to the concept."],
                "difficulty": "advanced",
                "research_source_ids": ["src_1"],
            },
            "changed the supplied learner difficulty",
        ),
        (
            {
                "scenario": "A real scenario.",
                "practical_task": "Apply the concept.",
                "real_world_context": "An application context.",
                "expected_action": "Explain your approach.",
                "success_criteria": ["Connect evidence to the concept."],
                "difficulty": "beginner",
                "research_source_ids": ["another-session-source"],
            },
            "outside the session research package",
        ),
    ],
)
def test_kira_rejects_changed_difficulty_and_unowned_sources(data, message):
    provider = MockAIProvider(
        custom_responses={KiraGeneratedPractical.__name__: data}
    )
    with pytest.raises(KiraResponseError, match=message):
        KiraPracticalAgent(provider).create_activity(_task())
