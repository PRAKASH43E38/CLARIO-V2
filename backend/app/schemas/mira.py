from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.research import ResearchConcept, SharedResearchPackage


LearnerLevel = Literal["beginner", "intermediate", "advanced"]


class MiraRemediationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str
    weakness_evidence: str
    previous_explanation: str
    previous_examples: list[str]
    current_difficulty: Literal["EASY", "MEDIUM", "HARD"]
    remediation_attempt: int = Field(ge=1)


class MiraTeachingTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    task: str
    learning_goal: str
    learner_state: str
    interest: str
    current_concept: ResearchConcept
    shared_research_package: SharedResearchPackage
    current_level: LearnerLevel
    learning_preference: Optional[str] = None
    remediation: MiraRemediationMetadata | None = None
    teaching_instruction: str


class MiraGeneratedTeaching(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str
    explanation: str
    key_points: list[str] = Field(min_length=1)
    examples: list[str] = Field(min_length=1)
    learner_level: LearnerLevel
    teaching_style: str
    source_reference_ids: list[str] = Field(default_factory=list)


class MiraSourceReference(BaseModel):
    source_id: str
    title: str
    url: str


class MiraTeachingResponse(BaseModel):
    session_id: str
    concept: str
    explanation: str
    key_points: list[str]
    examples: list[str]
    learner_level: LearnerLevel
    teaching_style: str
    source_references: list[MiraSourceReference]
    generated_at: datetime
