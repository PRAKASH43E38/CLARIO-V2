from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel
from backend.app.schemas.evaluation import MasterEvaluation

class AdaptiveAction(str, Enum):
    ADVANCE = "advance"
    REMEDIATE = "remediate"
    CONTINUE = "continue"
    TOPIC_COMPLETED = "topic_completed"

class AdaptiveDecision(BaseModel):
    action: AdaptiveAction
    target_concept_title: str
    target_concept_id: Optional[str] = None
    new_status: str  # "mastered", "remediating", "learning"
    new_difficulty: int
    attempt_number: int
    remediation_notes: Optional[str] = None
    reason: str

class AdaptivePolicy:
    """Deterministic adaptive decision rules for CLARIO.
    Implements ADR-005:
    - Mastery: Score >= 80.0 -> 'mastered'
    - Weakness: Score < 60.0 or Ellara remediation_required -> 'remediating'
    - Difficulty adjusts deterministically (-1 on weak, +1 on high mastery)
    - Isolates weak concepts without restarting topic.
    """

    MASTERY_THRESHOLD: float = 80.0
    HIGH_MASTERY_THRESHOLD: float = 85.0
    REMEDIATION_THRESHOLD: float = 60.0
    MIN_DIFFICULTY: int = 1
    MAX_DIFFICULTY: int = 5

    @classmethod
    def evaluate(
        cls,
        concept_title: str,
        current_status: str,
        current_difficulty: int,
        attempt_count: int,
        evaluation: MasterEvaluation,
        quiz_score: float,
    ) -> AdaptiveDecision:
        next_attempt = attempt_count + 1

        # Determine if concept is weak based on score and Ellara's diagnostic
        is_weak = (
            quiz_score < cls.REMEDIATION_THRESHOLD
            or evaluation.remediation_required
            or concept_title in evaluation.weak_concepts
        )

        # Determine if concept is mastered
        is_mastered = (
            quiz_score >= cls.MASTERY_THRESHOLD
            and not evaluation.remediation_required
            and concept_title not in evaluation.weak_concepts
        )

        if is_weak:
            # Difficulty decrease on weakness
            new_difficulty = max(cls.MIN_DIFFICULTY, current_difficulty - 1)
            misconceptions_str = ", ".join(evaluation.misconceptions) if evaluation.misconceptions else "None noted"
            notes = (
                f"Remediation round {next_attempt} for '{concept_title}'. "
                f"Previous score: {quiz_score:.1f}%. "
                f"Focus on addressing misconceptions: {misconceptions_str}."
            )
            return AdaptiveDecision(
                action=AdaptiveAction.REMEDIATE,
                target_concept_title=concept_title,
                new_status="remediating",
                new_difficulty=new_difficulty,
                attempt_number=next_attempt,
                remediation_notes=notes,
                reason=f"Score {quiz_score:.1f}% or Ellara flagged remediation needed.",
            )

        elif is_mastered:
            # Difficulty increase if high mastery demonstrated
            if quiz_score >= cls.HIGH_MASTERY_THRESHOLD:
                new_difficulty = min(cls.MAX_DIFFICULTY, current_difficulty + 1)
            else:
                new_difficulty = current_difficulty

            return AdaptiveDecision(
                action=AdaptiveAction.ADVANCE,
                target_concept_title=concept_title,
                new_status="mastered",
                new_difficulty=new_difficulty,
                attempt_number=next_attempt,
                remediation_notes=None,
                reason=f"Score {quiz_score:.1f}% meets mastery threshold ({cls.MASTERY_THRESHOLD}%).",
            )

        else:
            # Score is between 60.0 and 79.9
            # If was already remediating, learner remains in remediation until >= 80%
            if current_status == "remediating":
                return AdaptiveDecision(
                    action=AdaptiveAction.REMEDIATE,
                    target_concept_title=concept_title,
                    new_status="remediating",
                    new_difficulty=current_difficulty,
                    attempt_number=next_attempt,
                    remediation_notes=f"Continuing remediation for '{concept_title}'. Score {quiz_score:.1f}% requires >= {cls.MASTERY_THRESHOLD}% to master.",
                    reason="Moderate score during remediation requires further practice.",
                )
            else:
                return AdaptiveDecision(
                    action=AdaptiveAction.CONTINUE,
                    target_concept_title=concept_title,
                    new_status="learning",
                    new_difficulty=current_difficulty,
                    attempt_number=next_attempt,
                    remediation_notes=None,
                    reason=f"Score {quiz_score:.1f}% indicates partial understanding; continuing practice.",
                )
