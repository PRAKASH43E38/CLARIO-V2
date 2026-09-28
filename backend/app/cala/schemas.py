from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

LearnerLevel = Literal["beginner", "intermediate", "advanced"]
ConfidenceLevel = Literal["unknown", "low", "moderate", "high"]
CompletionState = Literal["not_started", "in_progress", "completed"]
RoadmapLevelState = Literal[
    "LEVEL_LOCKED",
    "LEVEL_UNLOCKED",
    "LEVEL_ENTERED",
    "LEVEL_RESEARCH",
    "LEVEL_COMPLETED",
]


class ConfidenceState(BaseModel):
    level: ConfidenceLevel
    evidence: Optional[str] = None
    self_reported_score: Optional[int] = None


class RoadmapConcept(BaseModel):
    concept_id: str
    title: str
    description: str
    order: int


class RoadmapTopic(BaseModel):
    topic_id: str
    title: str
    description: Optional[str] = None
    order: int
    concepts: list[RoadmapConcept]


class RoadmapLevel(BaseModel):
    level_id: str
    title: str
    description: str
    order: int
    is_unlocked: bool
    completion_state: CompletionState
    topics: list[RoadmapTopic]
    level_state: RoadmapLevelState = "LEVEL_LOCKED"
    prerequisites: list[str] = Field(default_factory=list)
    owner_session_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def infer_legacy_level_state(cls, value):
        if not isinstance(value, dict) or value.get("level_state"):
            return value
        if value.get("completion_state") == "completed":
            state = "LEVEL_COMPLETED"
        elif value.get("completion_state") == "in_progress":
            state = "LEVEL_ENTERED"
        elif value.get("is_unlocked"):
            state = "LEVEL_UNLOCKED"
        else:
            state = "LEVEL_LOCKED"
        return {**value, "level_state": state}


class GeneratedCurriculumConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)


class GeneratedCurriculumTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    concepts: list[GeneratedCurriculumConcept] = Field(min_length=1)


class GeneratedCurriculumLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    topics: list[GeneratedCurriculumTopic] = Field(min_length=1)


class GeneratedRemainingCurriculum(BaseModel):
    model_config = ConfigDict(extra="forbid")

    levels: list[GeneratedCurriculumLevel]
    goal_complete: bool


class LevelProgressionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "COMPLETE_LEVEL",
        "UNLOCK_NEXT_LEVEL",
        "COMPLETE_GOAL",
        "LEVEL_ENTERED",
        "CONCEPT_ADVANCED",
    ]
    level_id: str
    concept_id: Optional[str] = None
    next_level_id: Optional[str] = None
    reason: str = Field(min_length=1, max_length=1200)
    occurred_at: datetime


class AgentRoutingStep(BaseModel):
    agent: Literal["Nova", "Mira", "Ayan", "Kira", "Zayn", "Elara"]
    purpose: str
    status: Literal["planned"] = "planned"


class CalaResult(BaseModel):
    session_id: str
    learner_level: LearnerLevel
    learner_level_reason: str
    weakness_type: str
    weakness_reason: str
    confidence_state: ConfidenceState
    recommended_starting_level: str
    recommended_starting_level_reason: str
    current_level_id: Optional[str] = None
    active_concept_id: Optional[str] = None
    active_attempt_number: int = Field(default=1, ge=1)
    curriculum_complete: bool = False
    progression_history: list[LevelProgressionEvent] = Field(default_factory=list)
    learning_goal: str
    task: str
    learner_state: str
    interest: str
    roadmap: list[RoadmapLevel]
    initial_agent_routing: list[AgentRoutingStep]


class LevelProgressionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["CONCEPT_ADVANCED", "UNLOCK_NEXT_LEVEL", "COMPLETE_GOAL"]
    level_id: str
    next_level_id: Optional[str] = None
    reason: str = Field(min_length=1, max_length=1200)
    plan: CalaResult
