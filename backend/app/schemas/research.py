from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResearchConcept(BaseModel):
    concept_id: str
    title: str
    description: str


class ResearchTopicContext(BaseModel):
    topic_id: str
    title: str
    concepts: list[ResearchConcept]


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    learning_goal: str
    task: str
    learner_state: str
    interest: str
    learner_level: Literal["beginner", "intermediate", "advanced"]
    recommended_starting_level: str
    current_topic: ResearchTopicContext
    research_objective: str


class ResearchSource(BaseModel):
    source_id: str
    title: str
    url: str
    domain: str
    snippet: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_type: str = "unknown"
    published_date: Optional[str] = None
    validation_status: Literal["validated"] = "validated"


class ResearchQueryResult(BaseModel):
    query: str
    result_count: int


class ResearchValidationInfo(BaseModel):
    status: Literal["complete", "partial", "no_sources"]
    candidates_received: int
    sources_validated: int
    sources_rejected: int
    duplicate_sources_removed: int
    maximum_sources_per_domain: int


class SharedResearchPackage(BaseModel):
    session_id: str
    research_request: ResearchRequest
    research_summary: str
    key_concepts: list[ResearchConcept]
    selected_sources: list[ResearchSource] = Field(max_length=10)
    research_timestamp: datetime
    queries: list[ResearchQueryResult]
    validation_information: ResearchValidationInfo

class KeyConceptItem(BaseModel):
    title: str = Field(description="Name of the sub-concept")
    description: str = Field(description="Concise definition of the sub-concept")
    base_difficulty: int = Field(default=1, ge=1, le=5, description="Difficulty level 1-5")

class ResearchOutput(BaseModel):
    topic: str = Field(description="Name of the topic researched")
    overview: str = Field(description="High-level pedagogical overview of the topic")
    key_concepts: List[KeyConceptItem] = Field(description="List of core sub-concepts")
    examples: List[str] = Field(description="Intuitive real-world examples")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite concepts")
