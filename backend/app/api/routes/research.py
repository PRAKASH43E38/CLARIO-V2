from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.clario_ai import (
    CalaPlanRequiredError,
    ClarioAIOrchestrator,
    ResearchConfigurationMissingError,
    ResearchDispatchError,
)
from backend.app.core.database import get_db
from backend.app.models.repositories import (
    CalaPlanRepository,
    ResearchPackageRepository,
    SessionRepository,
    UserRepository,
)
from backend.app.research.dependencies import get_tavily_search_provider
from backend.app.research.tavily import TavilySearchProvider
from backend.app.schemas.research import SharedResearchPackage

router = APIRouter(prefix="/api/v1", tags=["research"])


def _get_owned_session(session_id: str, user_id: str, db: Session):
    if not UserRepository.get_by_id(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    session = SessionRepository.get_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Learning session not found")
    return session


def _load_existing_package(session_id: str, db: Session):
    record = ResearchPackageRepository.get_by_session_id(db, session_id)
    if record:
        return SharedResearchPackage.model_validate_json(record.package_json)
    return None


@router.post(
    "/sessions/{session_id}/research",
    response_model=SharedResearchPackage,
)
async def create_research_package(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    search_provider: TavilySearchProvider | None = Depends(get_tavily_search_provider),
):
    session = _get_owned_session(session_id, user_id, db)
    plan_record = CalaPlanRepository.get_by_session_id(db, session.id)
    if not plan_record:
        raise HTTPException(
            status_code=409,
            detail="Create the CALA plan before requesting research.",
        )

    try:
        ClarioAIOrchestrator.initialize_from_cala(db, session.id)
        context = await ClarioAIOrchestrator.request_research(
            db, session.id, search_provider
        )
    except CalaPlanRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ResearchConfigurationMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchDispatchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if context.research_package is None:
        raise HTTPException(
            status_code=502, detail="CLARIO-AI completed without a research package."
        )
    return context.research_package


@router.get(
    "/sessions/{session_id}/research",
    response_model=SharedResearchPackage,
)
async def get_research_package(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _get_owned_session(session_id, user_id, db)
    package = _load_existing_package(session.id, db)
    if not package:
        raise HTTPException(status_code=404, detail="Research package not found.")
    return package
