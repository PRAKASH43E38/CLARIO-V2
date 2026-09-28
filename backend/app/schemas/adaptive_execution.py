from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.adaptive_decision import DecisionAction
from backend.app.agents.zayn.contracts import ZaynDifficulty, ZaynPresentation


class RemediationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    orchestration_id: str
    concept_id: str
    concept_name: str
    decision_id: str
    decision_type: DecisionAction
    reason: str = Field(min_length=1)
    previous_difficulty: ZaynDifficulty
    new_difficulty: ZaynDifficulty
    remediation_attempt: int = Field(ge=1)
    source_evaluation_id: str


class AdaptiveExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str
    session_id: str
    concept_id: str
    decision_type: DecisionAction
    status: Literal[
        "IN_PROGRESS",
        "AWAITING_SUBMISSION",
        "COMPLETED",
        "FAILED",
        "LIMIT_REACHED",
    ]
    remediation_context: RemediationContext
    error_message: str | None = None
    current_state: str
    quiz: ZaynPresentation | None = None
    updated_at: datetime
