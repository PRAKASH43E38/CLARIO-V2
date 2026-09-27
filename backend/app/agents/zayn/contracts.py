from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ZaynDifficulty = Literal["EASY", "MEDIUM", "HARD"]
ZAYN_TIME_LIMITS = {"EASY": 30, "MEDIUM": 60, "HARD": 90}


class ZaynTeachingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_name: str
    explanation: str
    key_points: list[str]


class ZaynThinkingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_name: str
    thinking_prompt: str
    expected_reasoning_focus: list[str]


class ZaynPracticalReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str
    practical_task: str
    real_world_context: str
    expected_action: str
    success_criteria: list[str]


class ZaynLearnerContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    learner_state: str
    interest: str


class ZaynTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    orchestration_id: str
    concept_id: str
    concept_name: str
    difficulty: ZaynDifficulty
    question_count: int = Field(default=5, ge=1, le=5)
    learning_objective: str
    teaching_result_reference: ZaynTeachingReference
    thinking_result_reference: ZaynThinkingReference
    practical_result_reference: ZaynPracticalReference
    research_source_ids: list[str]
    learner_context: ZaynLearnerContext


class ZaynQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=2)
    correct_answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    difficulty: ZaynDifficulty
    concept_id: str = Field(min_length=1)


class ZaynOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal["Zayn"]
    session_id: str
    orchestration_id: str
    concept_id: str
    difficulty: ZaynDifficulty
    time_limit_seconds: int = Field(gt=0)
    questions: list[ZaynQuestion]
    generated_at: datetime


class ZaynPresentationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    question: str
    options: list[str]
    difficulty: ZaynDifficulty
    concept_id: str


class ZaynPresentation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quiz_id: str
    session_id: str
    orchestration_id: str
    concept_id: str
    difficulty: ZaynDifficulty
    time_limit_seconds: int
    questions: list[ZaynPresentationQuestion]
    status: Literal["GENERATED", "IN_PROGRESS", "SUBMITTED"]
    created_at: datetime


class ZaynSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quiz_id: str = Field(min_length=1)
    answers: dict[str, str]


class ZaynSubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quiz_id: str
    status: Literal["SUBMITTED"]
    submitted_at: datetime


class ZaynAnswerKeyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correct_answer: str
    explanation: str
