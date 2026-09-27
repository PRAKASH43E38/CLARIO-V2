from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


KiraDifficulty = Literal["beginner", "intermediate", "advanced"]


class KiraLearnerContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    learner_state: str
    interest: str
    learner_level: KiraDifficulty


class KiraTeachingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str
    concept_name: str
    explanation: str
    key_points: list[str]
    examples: list[str]


class KiraThinkingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str
    concept_name: str
    thinking_prompt: str
    expected_reasoning_focus: list[str]


class KiraResearchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    snippet: str


class KiraTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    orchestration_id: str
    concept_id: str
    concept_name: str
    learning_objective: str
    teaching_result_reference: KiraTeachingReference
    thinking_result_reference: KiraThinkingReference
    research_source_ids: list[str]
    research_summary: str
    research_sources: list[KiraResearchSource]
    learner_context: KiraLearnerContext
    task_instruction: str


class KiraGeneratedPractical(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str = Field(min_length=1)
    practical_task: str = Field(min_length=1)
    real_world_context: str = Field(min_length=1)
    expected_action: str = Field(min_length=1)
    success_criteria: list[str] = Field(min_length=1)
    difficulty: KiraDifficulty
    research_source_ids: list[str]


class KiraOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal["Kira"]
    session_id: str
    orchestration_id: str
    concept_id: str
    scenario: str
    practical_task: str
    real_world_context: str
    expected_action: str
    success_criteria: list[str]
    difficulty: KiraDifficulty
    research_source_ids: list[str]
    generated_at: datetime
