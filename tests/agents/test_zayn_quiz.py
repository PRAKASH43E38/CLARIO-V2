import json

import pytest
from pydantic import ValidationError

from backend.app.agents.zayn import ZaynQuizAgent, ZaynResponseError, ZaynTask
from backend.app.agents.zayn.quiz import ZaynGeneratedQuiz
from backend.app.ai.mock_provider import MockAIProvider


def _task(difficulty="EASY"):
    return ZaynTask.model_validate({
        "session_id": "ses_1",
        "orchestration_id": "orch_1",
        "concept_id": "con_1",
        "concept_name": "Information Gain",
        "difficulty": difficulty,
        "question_count": 5,
        "learning_objective": "Explain how decision trees select splits",
        "teaching_result_reference": {
            "concept_name": "Information Gain",
            "explanation": "Compare the usefulness of potential splits.",
            "key_points": ["Compare candidate splits."],
        },
        "thinking_result_reference": {
            "concept_name": "Information Gain",
            "thinking_prompt": "Why might one split be more useful?",
            "expected_reasoning_focus": ["Explain how the split changes uncertainty."],
        },
        "practical_result_reference": {
            "scenario": "Choose a player statistic for a tree split.",
            "practical_task": "Explain how the statistic separates outcomes.",
            "real_world_context": "Sports analytics.",
            "expected_action": "Compare how candidate splits separate the data.",
            "success_criteria": ["Connect the evidence to the concept."],
        },
        "research_source_ids": ["src_1"],
        "learner_context": {
            "task": "Understand information gain",
            "learner_state": "I know basic probability",
            "interest": "Sports analytics",
        },
    })


@pytest.mark.parametrize(
    ("difficulty", "seconds"),
    [("EASY", 30), ("MEDIUM", 60), ("HARD", 90)],
)
def test_zayn_generates_five_current_concept_questions_at_requested_mode(
    difficulty, seconds
):
    provider = MockAIProvider()
    output = ZaynQuizAgent(provider).create_quiz(_task(difficulty))

    assert output.agent == "Zayn"
    assert output.session_id == "ses_1"
    assert output.orchestration_id == "orch_1"
    assert output.concept_id == "con_1"
    assert output.difficulty == difficulty
    assert output.time_limit_seconds == seconds
    assert len(output.questions) == 5
    for question in output.questions:
        assert question.concept_id == "con_1"
        assert question.difficulty == difficulty
        assert len(question.options) >= 2
        assert question.correct_answer in question.options
        assert question.explanation
    task_json = json.loads(
        provider.call_history[0]["prompt"].partition("Zayn quiz task:\n")[2]
    )
    assert task_json["concept_name"] == "Information Gain"
    assert task_json["practical_result_reference"]["scenario"]


def test_zayn_task_contract_rejects_extra_fields():
    task = _task().model_dump()
    task["manual_level"] = "advanced"
    with pytest.raises(ValidationError):
        ZaynTask.model_validate(task)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (
            {"questions": [], "difficulty": "EASY"},
            "exactly 5",
        ),
        (
            {
                "difficulty": "MEDIUM",
                "questions": [],
            },
            "changed the CLARIO-AI quiz difficulty",
        ),
        (
            {
                "difficulty": "EASY",
                "questions": [
                    {
                        "question_id": "q1",
                        "question": "Choose an approach.",
                        "options": ["A", "B"],
                        "correct_answer": "A",
                        "explanation": "Explanation.",
                        "difficulty": "EASY",
                        "concept_id": "con_1",
                    }
                ] * 5,
            },
            "duplicate question IDs",
        ),
        (
            {
                "difficulty": "EASY",
                "questions": [
                    {
                        "question_id": f"q{i}",
                        "question": "Choose an approach.",
                        "options": ["A", "A", "C"],
                        "correct_answer": "A",
                        "explanation": "Explanation.",
                        "difficulty": "EASY",
                        "concept_id": "con_1",
                    }
                    for i in range(5)
                ],
            },
            "duplicate answer options",
        ),
        (
            {
                "difficulty": "EASY",
                "questions": [
                    {
                        "question_id": f"q{i}",
                        "question": "Choose an approach.",
                        "options": ["A", "B"],
                        "correct_answer": "not-an-option",
                        "explanation": "Explanation.",
                        "difficulty": "EASY",
                        "concept_id": "con_1",
                    }
                    for i in range(5)
                ],
            },
            "exactly",
        ),
        (
            {
                "difficulty": "EASY",
                "questions": [
                    {
                        "question_id": f"q{i}",
                        "question": "Choose an approach.",
                        "options": ["A", "B"],
                        "correct_answer": "A",
                        "explanation": "Explanation.",
                        "difficulty": "EASY",
                        "concept_id": "another-concept",
                    }
                    for i in range(5)
                ],
            },
            "different concept",
        ),
    ],
)
def test_zayn_rejects_invalid_quiz_structure(response, message):
    provider = MockAIProvider(custom_responses={ZaynGeneratedQuiz.__name__: response})
    with pytest.raises(ZaynResponseError, match=message):
        ZaynQuizAgent(provider).create_quiz(_task())
