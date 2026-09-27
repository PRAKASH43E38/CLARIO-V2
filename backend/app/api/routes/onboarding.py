from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api.schemas import OnboardingRequest, OnboardingResponse, ErrorResponse
from backend.app.core.database import get_db
from backend.app.models.repositories import UserRepository, LearnerProfileRepository, CurriculumRepository
from backend.app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["onboarding"])


@router.post("/onboarding/submit", response_model=OnboardingResponse, responses={400: {"model": ErrorResponse}})
async def submit_onboarding(request: OnboardingRequest, db: Session = Depends(get_db)):
    email = f"learner_{request.learning_goal.lower().replace(' ', '_')[:20]}@clario.local"
    
    user = UserRepository.get_by_email(db, email)
    if not user:
        user = UserRepository.create(db, email=email, password_hash="local_dev")
    
    profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    if profile:
        profile = LearnerProfileRepository.update(
            db, profile,
            learning_goal=request.learning_goal,
            current_level=request.current_level,
            learning_preference=request.learning_preference,
            interests=",".join(request.interests),
            initial_confidence=request.initial_confidence,
        )
    else:
        profile = LearnerProfileRepository.create(
            db,
            user_id=user.id,
            learning_goal=request.learning_goal,
            current_level=request.current_level,
            learning_preference=request.learning_preference,
            interests=",".join(request.interests),
            initial_confidence=request.initial_confidence,
        )
    
    topics = CurriculumRepository.list_topics(db)
    if not topics:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No curriculum is available. Run database migrations and try again.",
        )
    recommended_topic = topics[0]
    
    return OnboardingResponse(
        user_id=user.id,
        profile_id=profile.id,
        recommended_topic=recommended_topic.title,
        topic_id=recommended_topic.id,
        next_action="start_session"
    )


@router.get("/onboarding/status", response_model=dict, responses={404: {"model": ErrorResponse}})
async def onboarding_status(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    return {
        "status": "success",
        "onboarding_complete": profile is not None,
        "profile_id": profile.id if profile else None
    }