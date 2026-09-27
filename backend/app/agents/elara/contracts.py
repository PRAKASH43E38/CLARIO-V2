from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.agents.zayn.contracts import ZaynDifficulty


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
DifficultySignal = Literal["increase", "maintain", "decrease", "insufficient_evidence"]


class ElaraLearnerContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    goal: str
    learner_state: str
    interest: str
    learner_level: Literal["beginner", "intermediate", "advanced"]


class ElaraTeachingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str
    concept_name: str
    learning_objective: str
    explanation: str
    key_points: list[str]


class ElaraThinkingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str
    concept_name: str
    thinking_prompt: str
    expected_reasoning_focus: list[str]
    learner_response_status: Literal["unavailable"] = "unavailable"


class ElaraPracticalReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str
    concept_id: str
    scenario: str
    practical_task: str
    real_world_context: str
    expected_action: str
    success_criteria: list[str]
    learner_response_status: Literal["unavailable"] = "unavailable"


class ElaraQuizPerformance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quiz_result_id: str
    difficulty: ZaynDifficulty
    total_questions: int = Field(ge=1)
    answered_questions: int = Field(ge=0)
    unanswered_questions: int = Field(ge=0)
    correct_answers: int = Field(ge=0)
    incorrect_answers: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=100)


class ElaraQuizReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    performance: ElaraQuizPerformance


class ElaraTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    orchestration_id: str
    concept_id: str
    concept_name: str
    teaching_result_reference: ElaraTeachingReference
    thinking_result_reference: ElaraThinkingReference
    practical_result_reference: ElaraPracticalReference
    quiz_result_reference: ElaraQuizReference
    learner_context: ElaraLearnerContext


class ElaraOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal["Elara"]
    session_id: str
    orchestration_id: str
    concept_id: str
    concept_name: str
    concept_strength: ConceptStrength
    concept_weakness: ConceptWeakness
    quiz_performance: ElaraQuizPerformance
    thinking_evidence: Literal["unavailable"]
    practical_evidence: Literal["unavailable"]
    overall_evaluation: str = Field(min_length=1, max_length=1200)
    confidence: float = Field(ge=0, le=1)
    difficulty_signal: DifficultySignal
    evidence_summary: str = Field(min_length=1, max_length=1600)
    evaluated_at: datetime
