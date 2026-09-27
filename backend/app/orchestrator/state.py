from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from backend.app.schemas.research import ResearchOutput
from backend.app.schemas.teaching import TeachingOutput
from backend.app.schemas.thinking import CriticalThinkingQuestion, CriticalThinkingAssessment
from backend.app.schemas.practical import PracticalExercise
from backend.app.schemas.quiz import QuizQuestion, QuizGrading
from backend.app.schemas.evaluation import MasterEvaluation

class LearningStep(str, Enum):
    IDLE = "idle"
    RESEARCH = "research"
    TEACHING = "teaching"
    THINKING = "thinking"
    PRACTICAL = "practical"
    QUIZ = "quiz"
    EVALUATION = "evaluation"
    COMPLETED = "completed"

class ActiveSessionContext(BaseModel):
    session_id: str
    user_id: str
    profile_id: Optional[str] = None
    topic_id: str
    topic_title: str
    current_concept_id: Optional[str] = None
    current_concept_title: Optional[str] = None
    current_step: LearningStep = LearningStep.IDLE
    difficulty_level: int = 1

    # In-memory artifact cache for the active cycle
    research_data: Optional[ResearchOutput] = None
    teaching_data: Optional[TeachingOutput] = None
    thinking_question: Optional[CriticalThinkingQuestion] = None
    thinking_assessment: Optional[CriticalThinkingAssessment] = None
    practical_exercise: Optional[PracticalExercise] = None
    quiz_question: Optional[QuizQuestion] = None
    quiz_grading: Optional[QuizGrading] = None
    evaluation_result: Optional[MasterEvaluation] = None

    is_remediating: bool = False
    remediation_notes: Optional[str] = None
    attempt_count: int = 1
    asked_question_ids: List[str] = Field(default_factory=list)
    latest_decision: Optional[Any] = None
