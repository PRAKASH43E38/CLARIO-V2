from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from backend.app.api.schemas import (
    SessionCreateRequest, SessionCreateResponse, SessionStateResponse, ErrorResponse,
    SessionInputsRequest, SessionInputsResponse, LearningSessionCreateResponse,
)
from backend.app.core.database import get_db
from backend.app.models.session import Activity
from backend.app.models.repositories import (
    UserRepository, LearnerProfileRepository, CurriculumRepository, SessionRepository,
    MindProfileRepository, SessionInputsRepository,
)
from backend.app.orchestrator.nova import NovaOrchestrator
from backend.app.orchestrator.state import ActiveSessionContext, LearningStep
from backend.app.ai.factory import get_ai_provider

router = APIRouter(prefix="/api/v1", tags=["sessions"])


@router.post(
    "/learning-session/create",
    response_model=LearningSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_learning_session(
    request: SessionInputsRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.name:
        raise HTTPException(status_code=400, detail="Complete profile creation first.")
    mind_profile = MindProfileRepository.get_by_user_id(db, user.id)
    if not mind_profile:
        raise HTTPException(status_code=400, detail="Complete the five Mind Profile questions first.")

    topics = CurriculumRepository.list_topics(db)
    if not topics:
        raise HTTPException(status_code=503, detail="No curriculum is available.")
    topic = topics[0]
    concepts = CurriculumRepository.list_concepts_by_topic(db, topic.id)
    if not concepts:
        raise HTTPException(status_code=503, detail="The learning topic has no concepts.")

    profile = LearnerProfileRepository.get_or_create_learning_anchor(
        db,
        user_id=user.id,
        goal=request.goal,
        interest=request.interest,
        preferred_explanation=mind_profile.preferred_explanation,
    )
    session = SessionRepository.create_session(db, user.id, topic.id)
    SessionInputsRepository.create(db, session.id, **request.model_dump())
    return LearningSessionCreateResponse(
        session_id=session.id,
        topic_id=topic.id,
        topic_title=topic.title,
        inputs=SessionInputsResponse(**request.model_dump()),
    )


@router.post("/session/start", response_model=SessionCreateResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def start_session(request: SessionCreateRequest, user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete onboarding first")
    
    topic = CurriculumRepository.get_topic(db, request.topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    
    concepts = CurriculumRepository.list_concepts_by_topic(db, topic.id)
    if not concepts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected topic has no concepts and cannot start a learning session.",
        )
    first_concept = concepts[0]
    session = SessionRepository.create_session(db, user.id, topic.id)
    
    nova = NovaOrchestrator(ai_provider=get_ai_provider())
    ctx = ActiveSessionContext(
        session_id=session.id,
        user_id=user.id,
        profile_id=profile.id,
        topic_id=topic.id,
        topic_title=topic.title,
        current_concept_id=first_concept.id,
        current_concept_title=first_concept.title,
        difficulty_level=first_concept.base_difficulty,
    )
    
    ctx = nova.start_learning_flow(ctx, db=db, learner_level=profile.current_level, learning_preference=profile.learning_preference)
    
    return SessionCreateResponse(
        session_id=session.id,
        topic_id=topic.id,
        topic_title=topic.title
    )


@router.get("/session/{session_id}/state", response_model=SessionStateResponse, responses={404: {"model": ErrorResponse}})
async def get_session_state(session_id: str, db: Session = Depends(get_db)):
    sess = SessionRepository.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    profile = LearnerProfileRepository.get_by_user_id(db, sess.user_id)
    latest_activity = (
        db.query(Activity)
        .filter(Activity.session_id == sess.id, Activity.concept_id.isnot(None))
        .order_by(Activity.created_at.desc())
        .first()
    )
    topic_concepts = CurriculumRepository.list_concepts_by_topic(db, sess.topic_id)
    current_concept = (
        latest_activity.concept
        if latest_activity and latest_activity.concept
        else (topic_concepts[0] if topic_concepts else None)
    )
    latest_activity_type = latest_activity.companion_type if latest_activity else None
    step_map = {
        "teaching": LearningStep.TEACHING,
        "thinking": LearningStep.THINKING,
        "practical": LearningStep.PRACTICAL,
        "quiz": LearningStep.QUIZ,
    }
    current_step = step_map.get(latest_activity_type, LearningStep.IDLE)
    current_action_map = {
        LearningStep.TEACHING: "Review the lesson, then continue to the thinking activity.",
        LearningStep.THINKING: "Submit your reasoning about the current concept.",
        LearningStep.PRACTICAL: "Apply the concept to the practical exercise.",
        LearningStep.QUIZ: "Answer the assessment question.",
        LearningStep.IDLE: "This session has not started a learning activity yet.",
    }
    current_content = (
        json.loads(latest_activity.content_payload) if latest_activity else None
    )
    stored_inputs = sess.session_inputs
    ctx = ActiveSessionContext(
        session_id=sess.id,
        user_id=sess.user_id,
        profile_id=profile.id if profile else None,
        topic_id=sess.topic_id,
        topic_title=sess.topic.title if sess.topic else "",
        current_concept_id=current_concept.id if current_concept else None,
        current_concept_title=current_concept.title if current_concept else None,
        current_step=current_step,
        difficulty_level=(
            current_concept.base_difficulty
            if current_concept
            else 1
        ),
    )
    
    return SessionStateResponse(
        session_id=ctx.session_id,
        user_id=ctx.user_id,
        profile_id=ctx.profile_id,
        topic_id=ctx.topic_id,
        topic_title=ctx.topic_title,
        current_concept_id=ctx.current_concept_id,
        current_concept_title=ctx.current_concept_title,
        current_step=ctx.current_step.value,
        current_action=current_action_map[ctx.current_step],
        current_content=current_content,
        inputs=(
            SessionInputsResponse(
                task=stored_inputs.task,
                goal=stored_inputs.goal,
                learner_state=stored_inputs.learner_state,
                interest=stored_inputs.interest,
            )
            if stored_inputs
            else None
        ),
        difficulty_level=ctx.difficulty_level,
        is_remediating=ctx.is_remediating,
        remediation_notes=ctx.remediation_notes,
        attempt_count=ctx.attempt_count,
        asked_question_ids=ctx.asked_question_ids,
    )