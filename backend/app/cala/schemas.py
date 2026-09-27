from typing import Literal, Optional

from pydantic import BaseModel

LearnerLevel = Literal["beginner", "intermediate", "advanced"]
ConfidenceLevel = Literal["unknown", "low", "moderate", "high"]
CompletionState = Literal["not_started", "in_progress", "completed"]


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
    learning_goal: str
    task: str
    learner_state: str
    interest: str
    roadmap: list[RoadmapLevel]
    initial_agent_routing: list[AgentRoutingStep]
