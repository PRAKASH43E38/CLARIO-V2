from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.ai.base import BaseAIProvider
from backend.app.ai.factory import get_ai_provider
from backend.app.clario_ai import (
    CalaPlanRequiredError,
    ClarioAIOrchestrator,
    ResearchConfigurationMissingError,
    ResearchDispatchError,
    ResearchPackageRequiredError,
    TeachingInProgressError,
    TeachingOutputInvalid,
    TeachingPersistenceFailure,
    TeachingProviderFailure,
    ThinkingInProgressError,
    ThinkingOutputInvalid,
    ThinkingPersistenceFailure,
    ThinkingPrerequisiteError,
    ThinkingProviderFailure,
    PracticalInProgressError,
    PracticalOutputInvalid,
    PracticalPersistenceFailure,
    PracticalPrerequisiteError,
    PracticalProviderFailure,
    InvalidQuizSubmissionError,
    QuizInProgressError,
    QuizOutputInvalid,
    QuizPersistenceFailure,
    QuizPrerequisiteError,
    QuizProviderFailure,
    QuizSubmissionConflict,
    EvaluationPrerequisiteError,
    EvaluationInProgressError,
    EvaluationProviderFailure,
    EvaluationOutputInvalid,
    EvaluationPersistenceFailure,
    DecisionPrerequisiteError,
    DecisionPersistenceFailure,
)
from backend.app.core.database import get_db
from backend.app.models.repositories import SessionRepository, UserRepository
from backend.app.research.dependencies import get_tavily_search_provider
from backend.app.research.tavily import TavilySearchProvider
from backend.app.schemas.orchestration import ClarioOrchestrationContext
from backend.app.schemas.mira import MiraTeachingResponse
from backend.app.schemas.ayan import AyanThinkingResponse
from backend.app.agents.kira.contracts import KiraOutput
from backend.app.agents.zayn.contracts import (
    ZaynPresentation,
    ZaynSubmissionRequest,
    ZaynSubmissionResponse,
)
from backend.app.agents.elara.contracts import ElaraOutput
from backend.app.schemas.adaptive_decision import (
    AdaptiveDecision,
    SessionConceptPerformance,
)

router = APIRouter(prefix="/api/v1", tags=["orchestration"])


def _get_owned_session(session_id: str, user_id: str, db: Session):
    if not UserRepository.get_by_id(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    session = SessionRepository.get_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Learning session not found")
    return session


def _translate_plan_error(exc: CalaPlanRequiredError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


def get_teaching_ai_provider() -> BaseAIProvider:
    return get_ai_provider()


@router.post(
    "/sessions/{session_id}/orchestration",
    response_model=ClarioOrchestrationContext,
)
async def initialize_orchestration(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return ClarioAIOrchestrator.initialize_from_cala(db, session.id)
    except CalaPlanRequiredError as exc:
        raise _translate_plan_error(exc) from exc


@router.get(
    "/sessions/{session_id}/orchestration",
    response_model=ClarioOrchestrationContext,
)
async def get_orchestration_state(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    state = ClarioAIOrchestrator.get_state(db, session.id)
    if state is None:
        raise HTTPException(status_code=404, detail="CLARIO-AI orchestration not found.")
    return state


@router.post(
    "/sessions/{session_id}/orchestration/research",
    response_model=ClarioOrchestrationContext,
)
async def request_orchestration_research(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    search_provider: TavilySearchProvider | None = Depends(get_tavily_search_provider),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return await ClarioAIOrchestrator.request_research(
            db, session.id, search_provider
        )
    except CalaPlanRequiredError as exc:
        raise _translate_plan_error(exc) from exc
    except ResearchConfigurationMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchDispatchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/orchestration/teach",
    response_model=ClarioOrchestrationContext,
)
async def request_orchestration_teaching(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    ai_provider: BaseAIProvider = Depends(get_teaching_ai_provider),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return await ClarioAIOrchestrator.request_teaching(
            db, session.id, ai_provider
        )
    except CalaPlanRequiredError as exc:
        raise _translate_plan_error(exc) from exc
    except ResearchPackageRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TeachingInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TeachingProviderFailure as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TeachingOutputInvalid as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TeachingPersistenceFailure as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/teaching",
    response_model=MiraTeachingResponse,
)
async def get_teaching_result(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    response = ClarioAIOrchestrator.get_teaching_result(db, session.id)
    if response is None:
        raise HTTPException(status_code=404, detail="Teaching result not found.")
    return response


@router.post(
    "/sessions/{session_id}/orchestration/think",
    response_model=ClarioOrchestrationContext,
)
async def request_orchestration_thinking(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    ai_provider: BaseAIProvider = Depends(get_teaching_ai_provider),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return await ClarioAIOrchestrator.request_thinking(
            db, session.id, ai_provider
        )
    except CalaPlanRequiredError as exc:
        raise _translate_plan_error(exc) from exc
    except ThinkingPrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ThinkingInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ThinkingProviderFailure as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ThinkingOutputInvalid as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ThinkingPersistenceFailure as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/thinking",
    response_model=AyanThinkingResponse,
)
async def get_thinking_result(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    response = ClarioAIOrchestrator.get_thinking_result(db, session.id)
    if response is None:
        raise HTTPException(status_code=404, detail="Thinking result not found.")
    return response


@router.post(
    "/sessions/{session_id}/orchestration/practical",
    response_model=ClarioOrchestrationContext,
)
async def request_orchestration_practical(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    ai_provider: BaseAIProvider = Depends(get_teaching_ai_provider),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return await ClarioAIOrchestrator.request_practical(
            db, session.id, ai_provider
        )
    except PracticalPrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PracticalInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PracticalProviderFailure as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except PracticalOutputInvalid as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except PracticalPersistenceFailure as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/practical",
    response_model=KiraOutput,
)
async def get_practical_result(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    response = ClarioAIOrchestrator.get_practical_result(db, session.id)
    if response is None:
        raise HTTPException(status_code=404, detail="Practical activity not found.")
    return response


@router.post(
    "/sessions/{session_id}/orchestration/quiz",
    response_model=ZaynPresentation,
)
async def request_orchestration_quiz(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    ai_provider: BaseAIProvider = Depends(get_teaching_ai_provider),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return await ClarioAIOrchestrator.request_quiz(db, session.id, ai_provider)
    except QuizPrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QuizInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QuizProviderFailure as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except QuizOutputInvalid as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except QuizPersistenceFailure as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/quiz",
    response_model=ZaynPresentation,
)
async def get_quiz_presentation(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    response = ClarioAIOrchestrator.get_quiz_presentation(db, session.id)
    if response is None:
        raise HTTPException(status_code=404, detail="Quiz not found.")
    return response


@router.post(
    "/sessions/{session_id}/quiz/submit",
    response_model=ZaynSubmissionResponse,
)
async def submit_quiz_answers(
    session_id: str,
    request: ZaynSubmissionRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return ClarioAIOrchestrator.submit_quiz(db, session.id, request)
    except QuizPrerequisiteError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidQuizSubmissionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QuizSubmissionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QuizPersistenceFailure as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/orchestration/evaluate",
    response_model=ElaraOutput,
)
async def request_orchestration_evaluation(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    ai_provider: BaseAIProvider = Depends(get_teaching_ai_provider),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return await ClarioAIOrchestrator.request_evaluation(
            db, session.id, ai_provider
        )
    except EvaluationPrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EvaluationInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EvaluationProviderFailure as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except EvaluationOutputInvalid as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except EvaluationPersistenceFailure as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/evaluation",
    response_model=ElaraOutput,
)
async def get_orchestration_evaluation(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    evaluation = ClarioAIOrchestrator.get_evaluation(db, session.id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found.")
    return evaluation


@router.post(
    "/sessions/{session_id}/orchestration/decide",
    response_model=AdaptiveDecision,
)
async def request_orchestration_decision(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    try:
        return ClarioAIOrchestrator.request_decision(db, session.id)
    except DecisionPrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DecisionPersistenceFailure as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/decision",
    response_model=AdaptiveDecision,
)
async def get_orchestration_decision(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    decision = ClarioAIOrchestrator.get_decision(db, session.id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Adaptive decision not found.")
    return decision


@router.get(
    "/sessions/{session_id}/concept-performance",
    response_model=list[SessionConceptPerformance],
)
async def get_session_concept_performance(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    return ClarioAIOrchestrator.get_concept_performance(db, session.id)
