from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.agents.zayn.contracts import ZaynDifficulty


DecisionAction = Literal[
    "CONTINUE",
    "RETEACH",
    "RETEST",
    "REDUCE_DIFFICULTY",
    "INCREASE_DIFFICULTY",
    "COMPLETE_LEVEL",
    "UNLOCK_NEXT_LEVEL",
    "COMPLETE_GOAL",
]
MasteryStatus = Literal["learning", "mastered", "remediating"]
ConceptStrength = Literal["strong", "moderate", "weak", "insufficient_evidence"]
ConceptWeakness = Literal[
    "none",
    "conceptual",
    "reasoning",
    "practical",
    "recall",
    "mixed",
    "insufficient_evidence",
]


class AdaptiveDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    orchestration_id: str
    level_id: str | None = None
    concept_id: str
    decision: DecisionAction
    mastery_status: MasteryStatus
    current_difficulty: ZaynDifficulty
    next_difficulty: ZaynDifficulty
    reason: str = Field(min_length=1, max_length=1200)
    evaluation_reference: str
    remediation_required: bool
    decided_at: datetime


class SessionConceptPerformance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    orchestration_id: str
    concept_id: str
    concept_name: str
    current_difficulty: ZaynDifficulty
    mastery_status: MasteryStatus
    strength: ConceptStrength
    weakness: ConceptWeakness
    evaluation_confidence: float = Field(ge=0, le=1)
    quiz_accuracy: float = Field(ge=0, le=100)
    attempt_count: int = Field(ge=0)
    remediation_count: int = Field(ge=0)
    last_evaluation_id: str
    created_at: datetime
    updated_at: datetime
