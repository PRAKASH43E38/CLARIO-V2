from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.api.schemas import (
    LearnerProfileResponse, ErrorResponse, UserProfileRequest, UserProfileResponse,
    MindProfileRequest, MindProfileResponse,
)
from backend.app.core.database import get_db
from backend.app.models.repositories import (
    UserRepository, LearnerProfileRepository, MindProfileRepository,
)
from backend.app.models.user import User

router = APIRouter(prefix="/api/v1/learner", tags=["learner"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.name:
        raise HTTPException(status_code=404, detail="Profile not found")
    return UserProfileResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        gender=user.gender or "",
        basic_details=user.basic_details,
        authentication_provider=user.authentication_provider,
    )


@router.put("/profile", response_model=UserProfileResponse)
async def save_user_profile(
    request: UserProfileRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user = UserRepository.update_profile(
        db,
        user,
        name=request.name.strip(),
        gender=request.gender.strip(),
        basic_details=request.basic_details.strip() if request.basic_details else None,
    )
    return UserProfileResponse(
        user_id=user.id,
        email=user.email,
        name=user.name or "",
        gender=user.gender or "",
        basic_details=user.basic_details,
        authentication_provider=user.authentication_provider,
    )


@router.get("/mind-profile", response_model=MindProfileResponse)
async def get_mind_profile(user_id: str, db: Session = Depends(get_db)):
    profile = MindProfileRepository.get_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Mind profile not found")
    return profile


@router.put("/mind-profile", response_model=MindProfileResponse)
async def save_mind_profile(
    request: MindProfileRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.name:
        raise HTTPException(status_code=400, detail="Complete profile creation first.")
    if MindProfileRepository.get_by_user_id(db, user.id):
        raise HTTPException(status_code=409, detail="Mind Profile can only be completed once.")
    try:
        profile = MindProfileRepository.create(db, user_id, **request.model_dump())
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Mind Profile can only be completed once.",
        ) from exc
    return profile


@router.get("/learner/profile", response_model=LearnerProfileResponse, responses={404: {"model": ErrorResponse}})
async def get_learner_profile(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    
    return LearnerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        learning_goal=profile.learning_goal,
        current_level=profile.current_level,
        learning_preference=profile.learning_preference,
        interests=profile.interests,
        initial_confidence=profile.initial_confidence,
        updated_at=profile.updated_at
    )