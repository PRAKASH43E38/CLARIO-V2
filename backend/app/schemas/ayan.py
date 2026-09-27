from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.mira import MiraTeachingResponse, MiraSourceReference


ThinkingDifficulty = Literal["beginner", "intermediate", "advanced"]


class AyanCriticalThinkingTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    concept: str
    learning_goal: str
    learner_state: str
    interest: str
    current_level: ThinkingDifficulty
    mira_teaching_result: MiraTeachingResponse
    research_source_references: list[MiraSourceReference]
    critical_thinking_instruction: str


class AyanGeneratedThinking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str = Field(min_length=1)
    thinking_prompt: str = Field(min_length=1)
    expected_reasoning_focus: list[str] = Field(min_length=1)
    difficulty: ThinkingDifficulty
    source_reference_ids: list[str] = Field(default_factory=list)


class AyanThinkingResponse(BaseModel):
    session_id: str
    concept: str
    thinking_prompt: str
    expected_reasoning_focus: list[str]
    difficulty: ThinkingDifficulty
    source_references: list[MiraSourceReference]
    generated_at: datetime
