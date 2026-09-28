from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


class OnboardingRequest(BaseModel):
    learning_goal: str = Field(..., min_length=1, description="What the learner wants to achieve")
    current_level: Literal["beginner", "intermediate", "advanced"] = Field(..., description="Current proficiency level")
    learning_preference: Literal["step_by_step", "example_first", "practical_first"] = Field(..., description="Preferred learning style")
    interests: List[str] = Field(default_factory=list, description="Contextual domains for analogies")
    initial_confidence: int = Field(..., ge=1, le=5, description="Self-reported confidence 1-5")


class OnboardingResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    user_id: str
    profile_id: str
    recommended_topic: str
    topic_id: str
    next_action: Literal["start_session"]


class LearnerProfileResponse(BaseModel):
    id: str
    user_id: str
    learning_goal: str
    current_level: str
    learning_preference: str
    interests: str
    initial_confidence: int
    updated_at: datetime


class AuthRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=256)


class AuthResponse(BaseModel):
    user_id: str
    email: str
    authentication_provider: str
    profile_complete: bool
    mind_profile_complete: bool


class UserProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(..., min_length=1, max_length=50)
    basic_details: Optional[str] = Field(default=None, max_length=1000)


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    name: str
    gender: str
    basic_details: Optional[str] = None
    authentication_provider: str


class MindProfileRequest(BaseModel):
    learning_motivation: str = Field(..., min_length=1, max_length=500)
    preferred_explanation: str = Field(..., min_length=1, max_length=500)
    support_when_stuck: str = Field(..., min_length=1, max_length=500)
    feedback_preference: str = Field(..., min_length=1, max_length=500)
    challenge_preference: str = Field(..., min_length=1, max_length=500)


class MindProfileResponse(MindProfileRequest):
    id: str
    user_id: str
    created_at: datetime


class SessionInputsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str = Field(..., min_length=1, max_length=1000)
    goal: str = Field(..., min_length=1, max_length=1000)
    learner_state: str = Field(..., min_length=1, max_length=1000)
    interest: str = Field(..., min_length=1, max_length=500)


class SessionInputsResponse(SessionInputsRequest):
    pass


class SessionCreateRequest(BaseModel):
    topic_id: str


class SessionCreateResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    session_id: str
    topic_id: str
    topic_title: str


class LearningSessionCreateResponse(SessionCreateResponse):
    inputs: SessionInputsResponse


class SessionStateResponse(BaseModel):
    session_id: str
    user_id: str
    profile_id: Optional[str] = None
    topic_id: str
    topic_title: str
    current_concept_id: Optional[str] = None
    current_concept_title: Optional[str] = None
    current_step: str
    current_action: str
    current_content: Optional[Dict[str, Any]] = None
    inputs: Optional[SessionInputsResponse] = None
    difficulty_level: int
    is_remediating: bool
    remediation_notes: Optional[str] = None
    attempt_count: int
    asked_question_ids: List[str] = []


class ThinkingSubmitRequest(BaseModel):
    session_id: str
    learner_response: str


class ThinkingSubmitResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    session_id: str
    thinking_assessment: Dict[str, Any]
    practical_exercise: Dict[str, Any]
    next_step: Dict[str, Any]


class PracticalSubmitRequest(BaseModel):
    session_id: str
    learner_response: str


class QuizQuestionResponse(BaseModel):
    question_id: str
    format: str
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: str
    difficulty: int


class QuizGenerateResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    session_id: str
    question: QuizQuestionResponse


class QuizSubmitRequest(BaseModel):
    session_id: str
    learner_answer: str


class EvaluationResult(BaseModel):
    concept: str
    status: str
    reasoning_score: float
    misconceptions: List[str]


class NextStep(BaseModel):
    action: str
    companion: str
    concept: str
    instructions: str


class QuizSubmitResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    session_id: str
    evaluated_by: str
    evaluation: EvaluationResult
    next_step: NextStep


class ConceptBreakdownItem(BaseModel):
    concept: str
    status: str
    difficulty: int
    mastery_score: float


class DashboardResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    learner_name: str
    current_topic: str
    concept_breakdown: List[ConceptBreakdownItem]
    weak_concepts: List[str]
    recommended_action: str


class RoadmapItem(BaseModel):
    concept_id: str
    concept_title: str
    status: str
    difficulty: int
    is_next: bool


class RoadmapResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    current_topic: str
    topic_id: str
    roadmap: List[RoadmapItem]
    levels: List[dict] = Field(default_factory=list)
    current_level_id: Optional[str] = None
    active_concept_id: Optional[str] = None


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error: Dict[str, str]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "clario-api"
    version: str = "0.1.0"