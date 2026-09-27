from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.learner import LearnerProfile


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(user_id: str, db: Session = Depends(get_db)) -> str:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user_id


def get_learner_profile(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)) -> LearnerProfile:
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learner profile not found. Complete onboarding first."
        )
    return profile