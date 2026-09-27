import os
from pathlib import Path

BASE = Path(r"C:\clario\CLARIO-V2")

files = {}

# 1. ADR-006: REST and Streaming Strategy
files["docs/decisions/ADR-006-rest-and-streaming-strategy.md"] = """# ADR-006: REST Protocol and Streaming Strategy for MVP

## Status
Accepted

## Context
Phase 4 requires exposing all learning workflows through FastAPI. Previous discussions left streaming (SSE vs WebSockets) as DECISION PENDING.

## Decision
1. For MVP, use standard, predictable **REST endpoints with synchronous JSON responses**.
2. Each step in the companion cycle (`teaching`, `thinking`, `practical`, `quiz`, `evaluation`) is fetched or submitted via clean HTTP POST/GET requests.
3. Defer Server-Sent Events (SSE) and WebSockets until real-time character-by-character streaming is explicitly required by the frontend in Phase 5.

## Rationale
- Maximizes testability, reliability, and simplicity.
- Completely sufficient for turn-based companion UX.
- Avoids complex state synchronization and persistent connection management overhead.
"""

# 2. ADR-007: MVP Authentication Strategy
files["docs/decisions/ADR-007-mvp-auth-strategy.md"] = """# ADR-007: Lightweight Authentication Strategy for MVP

## Status
Accepted

## Context
Phase 4 requires authentication endpoints (`register`, `login`). We need a simple, self-contained auth mechanism that doesn't introduce external auth servers or heavy dependencies.

## Decision
1. Use standard password hashing (`hashlib.sha256` with salt or basic hashing) stored in the `users` table.
2. Provide `/auth/register` and `/auth/login` returning user information, profile ID, and an API token.
3. Authenticate requests via standard `user_id` parameter or `Authorization: Bearer <token>` header.

## Rationale
- Fully integrated with the existing `User` and `LearnerProfile` SQLite models.
- Clean and direct for MVP testing while remaining production-structured.
"""

# 3. backend/app/schemas/api.py
files["backend/app/schemas/api.py"] = """from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from backend.app.schemas.research import ResearchOutput
from backend.app.schemas.teaching import TeachingOutput
from backend.app.schemas.thinking import CriticalThinkingQuestion, CriticalThinkingAssessment
from backend.app.schemas.practical import PracticalExercise
from backend.app.schemas.quiz import QuizQuestion, QuizGrading
from backend.app.schemas.evaluation import MasterEvaluation
from backend.app.orchestrator.adaptive_policy import AdaptiveDecision

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: str
    message: str

class APIResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

# Auth Schemas
class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthData(BaseModel):
    user_id: str
    email: str
    profile_id: Optional[str] = None
    token: str

# Onboarding Schemas
class OnboardingSubmitRequest(BaseModel):
    user_id: str
    learning_goal: str
    current_level: str = "intermediate"
    learning_preference: str = "step_by_step"
    interests: str = "general"
    initial_confidence: int = 3

class OnboardingStatusData(BaseModel):
    is_completed: bool
    profile_id: Optional[str] = None

# Session Schemas
class CreateSessionRequest(BaseModel):
    user_id: str
    topic_id: str

class SessionStateData(BaseModel):
    session_id: str
    user_id: str
    profile_id: Optional[str] = None
    topic_id: str
    topic_title: str
    current_concept_id: Optional[str] = None
    current_concept_title: Optional[str] = None
    current_step: str
    difficulty_level: int
    is_remediating: bool
    remediation_notes: Optional[str] = None
    teaching_data: Optional[TeachingOutput] = None
    thinking_question: Optional[CriticalThinkingQuestion] = None
    thinking_assessment: Optional[CriticalThinkingAssessment] = None
    practical_exercise: Optional[PracticalExercise] = None
    quiz_question: Optional[QuizQuestion] = None
    quiz_grading: Optional[QuizGrading] = None
    evaluation_result: Optional[MasterEvaluation] = None
    latest_decision: Optional[AdaptiveDecision] = None

class ThinkingSubmitRequest(BaseModel):
    learner_response: str

class PracticalSubmitRequest(BaseModel):
    practical_submission: str

class QuizSubmitRequest(BaseModel):
    learner_answer: str

# Concept Performance Schemas
class ConceptPerformanceData(BaseModel):
    concept_id: str
    concept_title: Optional[str] = None
    status: str
    difficulty_level: int
    mastery_score: float
    attempt_count: int

# Dashboard Schemas
class ConceptBreakdownItem(BaseModel):
    concept_id: str
    concept_title: str
    status: str
    difficulty_level: int
    mastery_score: float

class DashboardData(BaseModel):
    learner_name: str
    current_topic: str
    overall_clarity_score: float
    concept_breakdown: List[ConceptBreakdownItem]
    strong_concepts: List[str]
    weak_concepts: List[str]
    recent_difficulty: int
    recommended_action: str

# Roadmap Schemas
class RoadmapConceptItem(BaseModel):
    concept_id: str
    title: str
    base_difficulty: int
    status: str

class RoadmapTopicItem(BaseModel):
    topic_id: str
    title: str
    sequence_order: int
    concepts: List[RoadmapConceptItem]

class RoadmapData(BaseModel):
    topics: List[RoadmapTopicItem]
    recommended_next_action: str
"""

# 4. Services
# backend/app/services/session_service.py
files["backend/app/services/session_service.py"] = """import hashlib
from typing import Dict, Optional
from sqlalchemy.orm import Session
from backend.app.orchestrator.nova import NovaOrchestrator
from backend.app.orchestrator.state import ActiveSessionContext, LearningStep
from backend.app.models.repositories import (
    SessionRepository,
    LearnerProfileRepository,
    CurriculumRepository,
    ConceptPerformanceRepository,
)

class SessionService:
    \"\"\"Manages learning session state and connects API routes to NovaOrchestrator.\"\"\"

    def __init__(self, nova: Optional[NovaOrchestrator] = None):
        self.nova = nova or NovaOrchestrator()
        # In-memory session context registry
        self._active_sessions: Dict[str, ActiveSessionContext] = {}

    def get_or_hydrate_context(self, db: Session, session_id: str) -> ActiveSessionContext:
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        session = SessionRepository.get_session(db, session_id)
        if not session:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        topic = CurriculumRepository.get_topic(db, session.topic_id)
        profile = LearnerProfileRepository.get_by_user_id(db, session.user_id)

        ctx = ActiveSessionContext(
            session_id=session.id,
            user_id=session.user_id,
            profile_id=profile.id if profile else None,
            topic_id=session.topic_id,
            topic_title=topic.title if topic else "General Topic",
        )
        self._active_sessions[session_id] = ctx
        return ctx

    def create_session(self, db: Session, user_id: str, topic_id: str) -> ActiveSessionContext:
        session = SessionRepository.create_session(db, user_id, topic_id)
        topic = CurriculumRepository.get_topic(db, topic_id)
        profile = LearnerProfileRepository.get_by_user_id(db, user_id)

        ctx = ActiveSessionContext(
            session_id=session.id,
            user_id=user_id,
            profile_id=profile.id if profile else None,
            topic_id=topic_id,
            topic_title=topic.title if topic else "General Topic",
        )
        self._active_sessions[session.id] = ctx
        return ctx

    def start_learning(self, db: Session, session_id: str) -> ActiveSessionContext:
        ctx = self.get_or_hydrate_context(db, session_id)
        profile = LearnerProfileRepository.get_by_user_id(db, ctx.user_id)
        level = profile.current_level if profile else "intermediate"
        pref = profile.learning_preference if profile else "step_by_step"

        ctx = self.nova.start_learning_flow(ctx, db=db, learner_level=level, learning_preference=pref)
        return ctx

    def proceed_to_thinking(self, db: Session, session_id: str) -> ActiveSessionContext:
        ctx = self.get_or_hydrate_context(db, session_id)
        return self.nova.proceed_to_thinking(ctx, db=db)

    def submit_thinking(self, db: Session, session_id: str, learner_response: str) -> ActiveSessionContext:
        ctx = self.get_or_hydrate_context(db, session_id)
        return self.nova.submit_thinking_response(ctx, learner_response, db=db)

    def proceed_to_quiz(self, db: Session, session_id: str) -> ActiveSessionContext:
        ctx = self.get_or_hydrate_context(db, session_id)
        return self.nova.proceed_to_quiz(ctx, db=db)

    def submit_quiz(self, db: Session, session_id: str, learner_answer: str) -> ActiveSessionContext:
        ctx = self.get_or_hydrate_context(db, session_id)
        return self.nova.submit_quiz_response(ctx, learner_answer, db=db)

    def trigger_remediation(self, db: Session, session_id: str) -> ActiveSessionContext:
        ctx = self.get_or_hydrate_context(db, session_id)
        return self.nova.trigger_targeted_remediation(ctx, db=db)

session_service = SessionService()
"""

# backend/app/services/dashboard_service.py
files["backend/app/services/dashboard_service.py"] = """from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.repositories import (
    UserRepository,
    LearnerProfileRepository,
    ConceptPerformanceRepository,
    CurriculumRepository,
)
from backend.app.schemas.api import DashboardData, ConceptBreakdownItem

class DashboardService:
    @staticmethod
    def get_dashboard(db: Session, user_id: str) -> DashboardData:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise ValueError(f"User '{user_id}' not found.")

        profile = LearnerProfileRepository.get_by_user_id(db, user_id)
        if not profile:
            return DashboardData(
                learner_name=user.email.split("@")[0],
                current_topic="Not Started",
                overall_clarity_score=0.0,
                concept_breakdown=[],
                strong_concepts=[],
                weak_concepts=[],
                recent_difficulty=1,
                recommended_action="Complete onboarding survey to start learning.",
            )

        perfs = ConceptPerformanceRepository.list_by_profile(db, profile.id)
        breakdown = []
        strong = []
        weak = []
        total_score = 0.0

        for p in perfs:
            concept = CurriculumRepository.get_concept(db, p.concept_id)
            title = concept.title if concept else "Unknown Concept"
            breakdown.append(ConceptBreakdownItem(
                concept_id=p.concept_id,
                concept_title=title,
                status=p.status,
                difficulty_level=p.difficulty_level,
                mastery_score=p.mastery_score,
            ))
            if p.status == "mastered":
                strong.append(title)
            elif p.status == "remediating":
                weak.append(title)
            total_score += p.mastery_score

        clarity_score = round(total_score / len(perfs), 1) if perfs else 0.0

        # Recommendation logic
        if weak:
            rec = f"Targeted remediation on weak concept: {weak[0]}"
        elif strong:
            rec = "Advance to the next concept in your learning path."
        else:
            rec = "Start your next learning session."

        recent_diff = perfs[-1].difficulty_level if perfs else 1

        return DashboardData(
            learner_name=user.email.split("@")[0],
            current_topic=profile.learning_goal or "General Curriculum",
            overall_clarity_score=clarity_score,
            concept_breakdown=breakdown,
            strong_concepts=strong,
            weak_concepts=weak,
            recent_difficulty=recent_diff,
            recommended_action=rec,
        )

dashboard_service = DashboardService()
"""

# backend/app/services/roadmap_service.py
files["backend/app/services/roadmap_service.py"] = """from sqlalchemy.orm import Session
from backend.app.models.repositories import (
    LearnerProfileRepository,
    CurriculumRepository,
    ConceptPerformanceRepository,
)
from backend.app.schemas.api import RoadmapData, RoadmapTopicItem, RoadmapConceptItem

class RoadmapService:
    @staticmethod
    def get_roadmap(db: Session, user_id: str) -> RoadmapData:
        profile = LearnerProfileRepository.get_by_user_id(db, user_id)
        topics = CurriculumRepository.list_topics(db)

        roadmap_topics = []
        perfs_by_concept = {}
        if profile:
            perfs = ConceptPerformanceRepository.list_by_profile(db, profile.id)
            perfs_by_concept = {p.concept_id: p.status for p in perfs}

        for t in topics:
            concepts = CurriculumRepository.list_concepts_by_topic(db, t.id)
            c_items = []
            for c in concepts:
                status = perfs_by_concept.get(c.id, "pending")
                c_items.append(RoadmapConceptItem(
                    concept_id=c.id,
                    title=c.title,
                    base_difficulty=c.base_difficulty,
                    status=status,
                ))
            roadmap_topics.append(RoadmapTopicItem(
                topic_id=t.id,
                title=t.title,
                sequence_order=t.sequence_order,
                concepts=c_items,
            ))

        next_action = "Select an available topic to begin."
        if profile:
            for t_item in roadmap_topics:
                for c_item in t_item.concepts:
                    if c_item.status == "remediating":
                        next_action = f"Remediate {c_item.title}"
                        break
                    elif c_item.status in ["learning", "pending"]:
                        next_action = f"Learn {c_item.title}"
                        break
                if next_action != "Select an available topic to begin.":
                    break

        return RoadmapData(
            topics=roadmap_topics,
            recommended_next_action=next_action,
        )

roadmap_service = RoadmapService()
"""

# backend/app/services/__init__.py
files["backend/app/services/__init__.py"] = """from backend.app.services.session_service import session_service, SessionService
from backend.app.services.dashboard_service import dashboard_service, DashboardService
from backend.app.services.roadmap_service import roadmap_service, RoadmapService

__all__ = [
    "session_service",
    "SessionService",
    "dashboard_service",
    "DashboardService",
    "roadmap_service",
    "RoadmapService",
]
"""

# 5. API Routers
# backend/app/api/v1/health.py
files["backend/app/api/v1/health.py"] = """from fastapi import APIRouter
from backend.app.schemas.api import APIResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=APIResponse[dict])
def check_health():
    return APIResponse(status="success", data={"service": "CLARIO Backend", "status": "healthy"})
"""

# backend/app/api/v1/auth.py
files["backend/app/api/v1/auth.py"] = """import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.repositories import UserRepository, LearnerProfileRepository
from backend.app.schemas.api import APIResponse, RegisterRequest, LoginRequest, AuthData, ErrorDetail

router = APIRouter(prefix="/auth", tags=["Auth"])

def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

@router.post("/register", response_model=APIResponse[AuthData])
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = UserRepository.get_by_email(db, req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    pw_hash = _hash_password(req.password)
    user = UserRepository.create(db, email=req.email, password_hash=pw_hash)
    token = f"tok_{user.id}"

    return APIResponse(
        status="success",
        data=AuthData(user_id=user.id, email=user.email, token=token),
    )

@router.post("/login", response_model=APIResponse[AuthData])
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = UserRepository.get_by_email(db, req.email)
    if not user or user.password_hash != _hash_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    token = f"tok_{user.id}"

    return APIResponse(
        status="success",
        data=AuthData(
            user_id=user.id,
            email=user.email,
            profile_id=profile.id if profile else None,
            token=token,
        ),
    )
"""

# backend/app/api/v1/onboarding.py
files["backend/app/api/v1/onboarding.py"] = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.repositories import UserRepository, LearnerProfileRepository
from backend.app.schemas.api import APIResponse, OnboardingSubmitRequest, OnboardingStatusData

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

@router.get("/status/{user_id}", response_model=APIResponse[OnboardingStatusData])
def get_onboarding_status(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    profile = LearnerProfileRepository.get_by_user_id(db, user_id)
    is_done = profile is not None

    return APIResponse(
        status="success",
        data=OnboardingStatusData(is_completed=is_done, profile_id=profile.id if profile else None),
    )

@router.post("/submit", response_model=APIResponse[OnboardingStatusData])
def submit_onboarding(req: OnboardingSubmitRequest, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, req.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{req.user_id}' not found.")

    existing_profile = LearnerProfileRepository.get_by_user_id(db, req.user_id)
    if existing_profile:
        profile = LearnerProfileRepository.update(
            db,
            existing_profile,
            learning_goal=req.learning_goal,
            current_level=req.current_level,
            learning_preference=req.learning_preference,
            interests=req.interests,
            initial_confidence=req.initial_confidence,
        )
    else:
        profile = LearnerProfileRepository.create(
            db,
            user_id=req.user_id,
            learning_goal=req.learning_goal,
            current_level=req.current_level,
            learning_preference=req.learning_preference,
            interests=req.interests,
            initial_confidence=req.initial_confidence,
        )

    return APIResponse(
        status="success",
        data=OnboardingStatusData(is_completed=True, profile_id=profile.id),
    )
"""

# backend/app/api/v1/session.py
files["backend/app/api/v1/session.py"] = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.session_service import session_service
from backend.app.schemas.api import (
    APIResponse,
    CreateSessionRequest,
    SessionStateData,
    ThinkingSubmitRequest,
    PracticalSubmitRequest,
    QuizSubmitRequest,
)

router = APIRouter(prefix="/session", tags=["Learning Session"])

def _to_session_data(ctx) -> SessionStateData:
    return SessionStateData(
        session_id=ctx.session_id,
        user_id=ctx.user_id,
        profile_id=ctx.profile_id,
        topic_id=ctx.topic_id,
        topic_title=ctx.topic_title,
        current_concept_id=ctx.current_concept_id,
        current_concept_title=ctx.current_concept_title,
        current_step=ctx.current_step.value if hasattr(ctx.current_step, "value") else str(ctx.current_step),
        difficulty_level=ctx.difficulty_level,
        is_remediating=ctx.is_remediating,
        remediation_notes=ctx.remediation_notes,
        teaching_data=ctx.teaching_data,
        thinking_question=ctx.thinking_question,
        thinking_assessment=ctx.thinking_assessment,
        practical_exercise=ctx.practical_exercise,
        quiz_question=ctx.quiz_question,
        quiz_grading=ctx.quiz_grading,
        evaluation_result=ctx.evaluation_result,
        latest_decision=ctx.latest_decision,
    )

@router.post("/create", response_model=APIResponse[SessionStateData])
def create_session(req: CreateSessionRequest, db: Session = Depends(get_db)):
    try:
        ctx = session_service.create_session(db, req.user_id, req.topic_id)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{session_id}/start", response_model=APIResponse[SessionStateData])
def start_session(session_id: str, db: Session = Depends(get_db)):
    try:
        ctx = session_service.start_learning(db, session_id)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{session_id}/state", response_model=APIResponse[SessionStateData])
def get_session_state(session_id: str, db: Session = Depends(get_db)):
    try:
        ctx = session_service.get_or_hydrate_context(db, session_id)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{session_id}/thinking/proceed", response_model=APIResponse[SessionStateData])
def proceed_to_thinking(session_id: str, db: Session = Depends(get_db)):
    try:
        ctx = session_service.proceed_to_thinking(db, session_id)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{session_id}/thinking/submit", response_model=APIResponse[SessionStateData])
def submit_thinking(session_id: str, req: ThinkingSubmitRequest, db: Session = Depends(get_db)):
    try:
        ctx = session_service.submit_thinking(db, session_id, req.learner_response)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{session_id}/practical/submit", response_model=APIResponse[SessionStateData])
def submit_practical(session_id: str, req: PracticalSubmitRequest, db: Session = Depends(get_db)):
    try:
        # Move forward to Quiz
        ctx = session_service.proceed_to_quiz(db, session_id)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{session_id}/quiz/proceed", response_model=APIResponse[SessionStateData])
def proceed_to_quiz(session_id: str, db: Session = Depends(get_db)):
    try:
        ctx = session_service.proceed_to_quiz(db, session_id)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{session_id}/quiz/submit", response_model=APIResponse[SessionStateData])
def submit_quiz(session_id: str, req: QuizSubmitRequest, db: Session = Depends(get_db)):
    try:
        ctx = session_service.submit_quiz(db, session_id, req.learner_answer)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{session_id}/evaluation", response_model=APIResponse[SessionStateData])
def get_evaluation(session_id: str, db: Session = Depends(get_db)):
    try:
        ctx = session_service.get_or_hydrate_context(db, session_id)
        return APIResponse(status="success", data=_to_session_data(ctx))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
"""

# backend/app/api/v1/concepts.py
files["backend/app/api/v1/concepts.py"] = """from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.repositories import ConceptPerformanceRepository, CurriculumRepository
from backend.app.schemas.api import APIResponse, ConceptPerformanceData

router = APIRouter(prefix="/concepts", tags=["Concepts"])

@router.get("/{profile_id}/performance", response_model=APIResponse[List[ConceptPerformanceData]])
def get_profile_concept_performance(profile_id: str, db: Session = Depends(get_db)):
    perfs = ConceptPerformanceRepository.list_by_profile(db, profile_id)
    data = []
    for p in perfs:
        c = CurriculumRepository.get_concept(db, p.concept_id)
        data.append(ConceptPerformanceData(
            concept_id=p.concept_id,
            concept_title=c.title if c else None,
            status=p.status,
            difficulty_level=p.difficulty_level,
            mastery_score=p.mastery_score,
            attempt_count=p.attempt_count,
        ))
    return APIResponse(status="success", data=data)
"""

# backend/app/api/v1/dashboard.py
files["backend/app/api/v1/dashboard.py"] = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.dashboard_service import dashboard_service
from backend.app.schemas.api import APIResponse, DashboardData

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/{user_id}", response_model=APIResponse[DashboardData])
def get_dashboard(user_id: str, db: Session = Depends(get_db)):
    try:
        data = dashboard_service.get_dashboard(db, user_id)
        return APIResponse(status="success", data=data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
"""

# backend/app/api/v1/roadmap.py
files["backend/app/api/v1/roadmap.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.roadmap_service import roadmap_service
from backend.app.schemas.api import APIResponse, RoadmapData

router = APIRouter(prefix="/roadmap", tags=["Roadmap"])

@router.get("/{user_id}", response_model=APIResponse[RoadmapData])
def get_roadmap(user_id: str, db: Session = Depends(get_db)):
    data = roadmap_service.get_roadmap(db, user_id)
    return APIResponse(status="success", data=data)
"""

# backend/app/api/v1/router.py
files["backend/app/api/v1/router.py"] = """from fastapi import APIRouter
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.onboarding import router as onboarding_router
from backend.app.api.v1.session import router as session_router
from backend.app.api.v1.concepts import router as concepts_router
from backend.app.api.v1.dashboard import router as dashboard_router
from backend.app.api.v1.roadmap import router as roadmap_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(onboarding_router)
api_v1_router.include_router(session_router)
api_v1_router.include_router(concepts_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(roadmap_router)
"""

# backend/app/api/v1/__init__.py
files["backend/app/api/v1/__init__.py"] = """from backend.app.api.v1.router import api_v1_router

__all__ = ["api_v1_router"]
"""

# 6. backend/app/main.py
files["backend/app/main.py"] = """from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from backend.app.core.config import settings
from backend.app.api.v1.router import api_v1_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="CLARIO: Adaptive Multi-Agent AI Learning Platform API",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global validation error handler returning predictable envelope
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc.errors()[0]["msg"]) if exc.errors() else "Validation failed",
            },
        },
    )

# Include v1 routes
app.include_router(api_v1_router)

@app.get("/")
def root():
    return {
        "service": "CLARIO API",
        "docs_url": "/docs",
        "api_v1": "/api/v1",
    }
"""

# Write all files
for rel_path, content in files.items():
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

print(f"Successfully generated {len(files)} Phase 4 files.")
