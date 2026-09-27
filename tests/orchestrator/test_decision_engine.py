from datetime import datetime, timezone

import pytest

from backend.app.agents.elara.contracts import ElaraOutput, ElaraQuizPerformance
from backend.app.clario_ai.decision_engine import decide_concept_outcome


def _evaluation(
    strength="strong",
    weakness="none",
    accuracy=80,
    confidence=0.7,
    signal="maintain",
):
    return ElaraOutput(
        agent="Elara",
        session_id="session_1",
        orchestration_id="orchestration_1",
        concept_id="concept_1",
        concept_name="Concept",
        concept_strength=strength,
        concept_weakness=weakness,
        quiz_performance=ElaraQuizPerformance(
            quiz_result_id="quiz_1",
            difficulty="MEDIUM",
            total_questions=5,
            answered_questions=5,
            unanswered_questions=0,
            correct_answers=4,
            incorrect_answers=1,
            accuracy=accuracy,
        ),
        thinking_evidence="unavailable",
        practical_evidence="unavailable",
        overall_evaluation="Evaluation summary.",
        confidence=confidence,
        difficulty_signal=signal,
        evidence_summary="Evidence summary.",
        evaluated_at=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize(
    ("strength", "weakness", "accuracy", "confidence", "signal", "expected"),
    [
        ("strong", "none", 80, 0.70, "maintain", "CONTINUE"),
        ("weak", "conceptual", 90, 0.95, "maintain", "RETEACH"),
        ("weak", "reasoning", 40, 0.8, "decrease", "REDUCE_DIFFICULTY"),
        (
            "insufficient_evidence",
            "insufficient_evidence",
            100,
            0.9,
            "insufficient_evidence",
            "RETEST",
        ),
        ("moderate", "none", 79.99, 0.9, "maintain", "RETEST"),
        ("strong", "none", 95, 0.9, "increase", "INCREASE_DIFFICULTY"),
    ],
)
def test_deterministic_decision_rules(
    strength, weakness, accuracy, confidence, signal, expected
):
    result = decide_concept_outcome(
        _evaluation(strength, weakness, accuracy, confidence, signal), "MEDIUM"
    )

    assert result.decision == expected
    assert result.current_difficulty == "MEDIUM"
    assert result.next_difficulty == {
        "REDUCE_DIFFICULTY": "EASY",
        "INCREASE_DIFFICULTY": "HARD",
    }.get(expected, "MEDIUM")


def test_mastery_requires_all_configured_evidence_conditions():
    for evaluation in (
        _evaluation(accuracy=79.99),
        _evaluation(confidence=0.69),
    ):
        result = decide_concept_outcome(evaluation, "EASY")
        assert result.decision == "RETEST"
        assert result.mastery_status == "learning"
    weak = decide_concept_outcome(_evaluation(weakness="recall"), "EASY")
    assert weak.decision == "RETEACH"
    assert weak.mastery_status == "remediating"


def test_increase_signal_can_raise_next_attempt_without_marking_mastery():
    result = decide_concept_outcome(
        _evaluation(accuracy=80, confidence=0.69, signal="increase"), "MEDIUM"
    )
    assert result.decision == "INCREASE_DIFFICULTY"
    assert result.next_difficulty == "HARD"
    assert result.mastery_status == "learning"


def test_weak_evidence_at_minimum_difficulty_reteaches_without_underflow():
    result = decide_concept_outcome(
        _evaluation("weak", "conceptual", signal="decrease"), "EASY"
    )
    assert result.decision == "RETEACH"
    assert result.next_difficulty == "EASY"
    assert result.mastery_status == "remediating"


def test_retest_preserves_remediating_status_and_difficulty():
    result = decide_concept_outcome(
        _evaluation("insufficient_evidence", "insufficient_evidence", signal="insufficient_evidence"),
        "MEDIUM",
        "remediating",
    )
    assert result.decision == "RETEST"
    assert result.mastery_status == "remediating"
    assert result.remediation_required
