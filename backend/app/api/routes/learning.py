from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.schemas import (
    ThinkingSubmitRequest, ThinkingSubmitResponse,
    PracticalSubmitRequest, QuizGenerateResponse, QuizSubmitRequest, QuizSubmitResponse,
    ErrorResponse
)
from backend.app.core.database import get_db
from backend.app.models.repositories import SessionRepository, ConceptPerformanceRepository
from backend.app.orchestrator.nova import NovaOrchestrator
from backend.app.orchestrator.state import ActiveSessionContext, LearningStep
from backend.app.ai.factory import get_ai_provider

router = APIRouter(prefix="/api/v1", tags=["learning"])


def _get_session_context(session_id: str, db: Session) -> ActiveSessionContext:
    sess = SessionRepository.get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    profile_id = sess.user_id
    profile = db.query(__import__('backend.app.models.learner', fromlist=['LearnerProfile']).LearnerProfile).filter(
        __import__('backend.app.models.learner', fromlist=['LearnerProfile']).LearnerProfile.user_id == sess.user_id
    ).first()
    if profile:
        profile_id = profile.id
    
    # Find the current concept from the session's activities
    # Get the latest activity with a concept_id
    Activity = __import__('backend.app.models.session', fromlist=['Activity']).Activity
    latest_activity = db.query(Activity).filter(
        Activity.session_id == sess.id,
        Activity.concept_id.isnot(None)
    ).order_by(Activity.created_at.desc()).first()
    
    current_concept_id = latest_activity.concept_id if latest_activity else None
    current_concept_title = latest_activity.concept.title if latest_activity and latest_activity.concept else None
    difficulty_level = latest_activity.concept.base_difficulty if latest_activity and latest_activity.concept else 1
    
    # Determine current step from the latest activity
    latest_activity_type = latest_activity.companion_type if latest_activity else None
    step_map = {
        "teaching": LearningStep.TEACHING,
        "thinking": LearningStep.THINKING,
        "practical": LearningStep.PRACTICAL,
        "quiz": LearningStep.QUIZ,
    }
    current_step = step_map.get(latest_activity_type, LearningStep.IDLE)
    
    ctx = ActiveSessionContext(
        session_id=sess.id,
        user_id=sess.user_id,
        profile_id=profile_id,
        topic_id=sess.topic_id,
        topic_title=sess.topic.title if sess.topic else "",
        current_concept_id=current_concept_id,
        current_concept_title=current_concept_title,
        current_step=current_step,
        difficulty_level=difficulty_level,
    )
    return ctx


@router.post("/session/action", response_model=dict, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def session_action(
    activity_id: str,
    companion_type: str,
    learner_response: str,
    db: Session = Depends(get_db)
):
    activity = db.query(__import__('backend.app.models.session', fromlist=['Activity']).Activity).filter(
        __import__('backend.app.models.session', fromlist=['Activity']).Activity.id == activity_id
    ).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    
    return await thinking_submit(ThinkingSubmitRequest(session_id=activity.session_id, learner_response=learner_response), db)


@router.post("/thinking/submit", response_model=ThinkingSubmitResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def thinking_submit(request: ThinkingSubmitRequest, db: Session = Depends(get_db)):
    ctx = _get_session_context(request.session_id, db)
    
    nova = NovaOrchestrator(ai_provider=get_ai_provider())
    ctx = nova.submit_thinking_response(ctx, request.learner_response, db=db)
    
    return ThinkingSubmitResponse(
        session_id=ctx.session_id,
        thinking_assessment={
            "reasoning_assessment": ctx.thinking_assessment.reasoning_assessment if ctx.thinking_assessment else "",
            "conceptual_understanding": ctx.thinking_assessment.conceptual_understanding if ctx.thinking_assessment else "low",
            "misconception": ctx.thinking_assessment.misconception if ctx.thinking_assessment else None,
            "confidence": ctx.thinking_assessment.confidence if ctx.thinking_assessment else 0.0,
        },
        practical_exercise={
            "scenario_title": ctx.practical_exercise.scenario_title if ctx.practical_exercise else "",
            "practical_type": ctx.practical_exercise.practical_type if ctx.practical_exercise else "",
            "scenario_description": ctx.practical_exercise.scenario_description if ctx.practical_exercise else "",
            "task_prompt": ctx.practical_exercise.task_prompt if ctx.practical_exercise else "",
            "hints": ctx.practical_exercise.hints if ctx.practical_exercise else [],
        },
        next_step={
            "action": "continue",
            "companion": "practical",
            "concept": ctx.current_concept_title or "",
            "instructions": ctx.practical_exercise.task_prompt if ctx.practical_exercise else "",
        }
    )


@router.post("/practical/submit", response_model=QuizGenerateResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def practical_submit(request: PracticalSubmitRequest, db: Session = Depends(get_db)):
    ctx = _get_session_context(request.session_id, db)
    
    nova = NovaOrchestrator(ai_provider=get_ai_provider())
    ctx = nova.proceed_to_quiz(ctx, db=db)
    
    return QuizGenerateResponse(
        session_id=ctx.session_id,
        question={
            "question_id": ctx.quiz_question.question_id if ctx.quiz_question else "",
            "format": ctx.quiz_question.format if ctx.quiz_question else "mcq",
            "question_text": ctx.quiz_question.question_text if ctx.quiz_question else "",
            "options": ctx.quiz_question.options if ctx.quiz_question else None,
            "correct_answer": ctx.quiz_question.correct_answer if ctx.quiz_question else "",
            "difficulty": ctx.quiz_question.difficulty if ctx.quiz_question else 1,
        }
    )


@router.post("/quiz/generate", response_model=QuizGenerateResponse, responses={404: {"model": ErrorResponse}})
async def quiz_generate(session_id: str, db: Session = Depends(get_db)):
    ctx = _get_session_context(session_id, db)
    
    nova = NovaOrchestrator(ai_provider=get_ai_provider())
    ctx = nova.proceed_to_quiz(ctx, db=db)
    
    return QuizGenerateResponse(
        session_id=ctx.session_id,
        question={
            "question_id": ctx.quiz_question.question_id if ctx.quiz_question else "",
            "format": ctx.quiz_question.format if ctx.quiz_question else "mcq",
            "question_text": ctx.quiz_question.question_text if ctx.quiz_question else "",
            "options": ctx.quiz_question.options if ctx.quiz_question else None,
            "correct_answer": ctx.quiz_question.correct_answer if ctx.quiz_question else "",
            "difficulty": ctx.quiz_question.difficulty if ctx.quiz_question else 1,
        }
    )


@router.post("/quiz/submit", response_model=QuizSubmitResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def quiz_submit(request: QuizSubmitRequest, db: Session = Depends(get_db)):
    ctx = _get_session_context(request.session_id, db)
    
    # Capture the concept being evaluated BEFORE NOVA updates the context
    evaluated_concept = ctx.current_concept_title
    
    nova = NovaOrchestrator(ai_provider=get_ai_provider())
    ctx = nova.submit_quiz_response(ctx, request.learner_answer, db=db)
    
    eval_result = ctx.evaluation_result
    latest_decision = ctx.latest_decision
    
    action = latest_decision.action.value if latest_decision else "continue"
    companion = "teaching" if action == "remediate" else "quiz"
    if action == "advance":
        companion = "teaching"
    elif action == "topic_completed":
        companion = "completed"
    
    return QuizSubmitResponse(
        session_id=ctx.session_id,
        evaluated_by="Ellara",
        evaluation={
            "concept": evaluated_concept or "",
            "status": latest_decision.new_status if latest_decision else "learning",
            "reasoning_score": ctx.quiz_grading.score if ctx.quiz_grading else 0.0,
            "misconceptions": eval_result.misconceptions if eval_result else [],
        },
        next_step={
            "action": action,
            "companion": companion,
            "concept": latest_decision.target_concept_title if latest_decision else ctx.current_concept_title or "",
            "instructions": latest_decision.remediation_notes if latest_decision and latest_decision.remediation_notes else (
                "Continue to next concept" if action == "advance" else "Review the concept"
            ),
        }
    )


@router.post("/remediation/trigger", response_model=dict, responses={404: {"model": ErrorResponse}})
async def trigger_remediation(session_id: str, db: Session = Depends(get_db)):
    ctx = _get_session_context(session_id, db)
    
    if not ctx.is_remediating:
        return {"status": "success", "message": "Not in remediation mode"}
    
    nova = NovaOrchestrator(ai_provider=get_ai_provider())
    ctx = nova.trigger_targeted_remediation(ctx, db=db)
    
    return {
        "status": "success",
        "session_id": ctx.session_id,
        "teaching_explanation": {
            "concept": ctx.teaching_data.concept if ctx.teaching_data else "",
            "explanation": ctx.teaching_data.explanation if ctx.teaching_data else "",
            "step_by_step_breakdown": ctx.teaching_data.step_by_step_breakdown if ctx.teaching_data else [],
            "analogy": ctx.teaching_data.analogy if ctx.teaching_data else None,
            "intuitive_example": ctx.teaching_data.intuitive_example if ctx.teaching_data else "",
            "check_for_understanding_prompt": ctx.teaching_data.check_for_understanding_prompt if ctx.teaching_data else "",
        }
    }