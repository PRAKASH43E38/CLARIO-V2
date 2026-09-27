from dataclasses import dataclass

from backend.app.agents.elara.contracts import ElaraOutput
from backend.app.agents.zayn.contracts import ZaynDifficulty
from backend.app.schemas.adaptive_decision import DecisionAction, MasteryStatus


DIFFICULTY_ORDER: tuple[ZaynDifficulty, ...] = ("EASY", "MEDIUM", "HARD")
MASTERY_ACCURACY_THRESHOLD = 80.0
MASTERY_CONFIDENCE_THRESHOLD = 0.70


@dataclass(frozen=True)
class DecisionAssessment:
    decision: DecisionAction
    mastery_status: MasteryStatus
    current_difficulty: ZaynDifficulty
    next_difficulty: ZaynDifficulty
    remediation_required: bool
    reason: str


def decide_concept_outcome(
    evaluation: ElaraOutput,
    current_difficulty: ZaynDifficulty,
    current_mastery_status: MasteryStatus | None = None,
) -> DecisionAssessment:
    """Apply explicit CLARIO-AI rules to one concept's persisted evaluation."""
    weak = evaluation.concept_strength == "weak" or evaluation.concept_weakness in {
        "conceptual",
        "reasoning",
        "practical",
        "recall",
        "mixed",
    }
    if weak:
        next_difficulty = current_difficulty
        if (
            evaluation.difficulty_signal == "decrease"
            and current_difficulty != "EASY"
        ):
            next_difficulty = DIFFICULTY_ORDER[
                DIFFICULTY_ORDER.index(current_difficulty) - 1
            ]
            decision: DecisionAction = "REDUCE_DIFFICULTY"
            reason = (
                "Elara identified weak evidence and signaled lower difficulty; "
                "CLARIO-AI selected a concept-specific difficulty reduction and reteaching."
            )
        else:
            decision = "RETEACH"
            reason = (
                "Elara identified weak evidence; CLARIO-AI selected reteaching "
                "for this concept without changing unrelated concepts."
            )
            if evaluation.difficulty_signal == "decrease":
                reason += " Difficulty is already at its minimum."
        return DecisionAssessment(
            decision=decision,
            mastery_status="remediating",
            current_difficulty=current_difficulty,
            next_difficulty=next_difficulty,
            remediation_required=True,
            reason=reason,
        )

    insufficient = (
        evaluation.concept_strength == "insufficient_evidence"
        or evaluation.concept_weakness == "insufficient_evidence"
        or evaluation.difficulty_signal == "insufficient_evidence"
    )
    if insufficient:
        return DecisionAssessment(
            decision="RETEST",
            mastery_status=(
                "remediating"
                if current_mastery_status == "remediating"
                else "learning"
            ),
            current_difficulty=current_difficulty,
            next_difficulty=current_difficulty,
            remediation_required=current_mastery_status == "remediating",
            reason=(
                "Evidence is insufficient for a mastery decision; CLARIO-AI "
                "requires a retest and does not mark this concept mastered."
            ),
        )

    mastery_condition_met = (
        evaluation.concept_strength == "strong"
        and evaluation.concept_weakness == "none"
        and evaluation.quiz_performance.accuracy >= MASTERY_ACCURACY_THRESHOLD
        and evaluation.confidence >= MASTERY_CONFIDENCE_THRESHOLD
    )
    if (
        evaluation.concept_strength == "strong"
        and evaluation.concept_weakness == "none"
        and evaluation.quiz_performance.accuracy >= MASTERY_ACCURACY_THRESHOLD
        and evaluation.difficulty_signal == "increase"
        and current_difficulty != "HARD"
    ):
        next_difficulty = DIFFICULTY_ORDER[
            DIFFICULTY_ORDER.index(current_difficulty) + 1
        ]
        return DecisionAssessment(
            decision="INCREASE_DIFFICULTY",
            mastery_status=(
                "mastered"
                if mastery_condition_met
                else (
                    "remediating"
                    if current_mastery_status == "remediating"
                    else "learning"
                )
            ),
            current_difficulty=current_difficulty,
            next_difficulty=next_difficulty,
            remediation_required=False,
            reason=(
                "Strong evidence, quiz accuracy of at least 80%, and Elara's "
                "increase signal warrant higher difficulty for the next attempt. "
                "The concept is mastered only if evaluation confidence is also "
                "at least 0.70."
            ),
        )

    if not mastery_condition_met:
        return DecisionAssessment(
            decision="RETEST",
            mastery_status=(
                "remediating"
                if current_mastery_status == "remediating"
                else "learning"
            ),
            current_difficulty=current_difficulty,
            next_difficulty=current_difficulty,
            remediation_required=current_mastery_status == "remediating",
            reason=(
                "The mastery condition (strong evidence, at least 80% quiz "
                "accuracy, and at least 0.70 evaluation confidence) is not met; "
                "CLARIO-AI requires a retest."
            ),
        )

    return DecisionAssessment(
        decision="CONTINUE",
        mastery_status="mastered",
        current_difficulty=current_difficulty,
        next_difficulty=current_difficulty,
        remediation_required=False,
        reason=(
            "Strong evidence, quiz accuracy of at least 80%, and evaluation "
            "confidence of at least 0.70 satisfy the concept mastery condition."
        ),
    )
