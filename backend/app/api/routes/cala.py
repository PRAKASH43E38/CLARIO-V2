from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.cala import CalaPlanner, CalaResult
from backend.app.core.database import get_db
from backend.app.models.repositories import (
    CalaPlanRepository,
    CurriculumRepository,
    LearnerProfileRepository,
    MindProfileRepository,
    SessionInputsRepository,
    SessionRepository,
    UserRepository,
)

router = APIRouter(prefix="/api/v1", tags=["cala"])


def _owned_session(session_id: str, user_id: str, db: Session):
    if not UserRepository.get_by_id(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    session = SessionRepository.get_session(db, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Learning session not found")
    return session


@router.post("/sessions/{session_id}/cala-plan", response_model=CalaResult)
async def create_cala_plan(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _owned_session(session_id, user_id, db)
    existing_plan = CalaPlanRepository.get_by_session_id(db, session.id)
    if existing_plan:
        return CalaResult.model_validate_json(existing_plan.plan_json)

    session_inputs = SessionInputsRepository.get_by_session_id(db, session.id)
    if not session_inputs:
        raise HTTPException(status_code=409, detail="Session inputs are not available.")

    topic = CurriculumRepository.get_topic(db, session.topic_id)
    if not topic:
        raise HTTPException(status_code=503, detail="The session curriculum is unavailable.")
    concepts = CurriculumRepository.list_concepts_by_topic(db, topic.id)
    if not concepts:
        raise HTTPException(status_code=503, detail="The session topic has no curriculum concepts.")

    plan = CalaPlanner.create_plan(
        session_id=session.id,
        session_inputs=session_inputs,
        topic=topic,
        concepts=concepts,
        mind_profile=MindProfileRepository.get_by_user_id(db, user_id),
        learner_profile=LearnerProfileRepository.get_by_user_id(db, user_id),
    )
    persisted_plan = CalaPlanRepository.create(
        db, session.id, plan.model_dump_json()
    )
    return CalaResult.model_validate_json(persisted_plan.plan_json)


@router.get("/sessions/{session_id}/cala-plan", response_model=CalaResult)
async def get_cala_plan(
    session_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    session = _owned_session(session_id, user_id, db)
    record = CalaPlanRepository.get_by_session_id(db, session.id)
    if not record:
        raise HTTPException(status_code=404, detail="CALA plan not found")
    return CalaResult.model_validate_json(record.plan_json)
