from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.app.core.database import get_db
from backend.app.models.thinking_result import ThinkingResultRecord
from backend.app.models.practical_result import PracticalResultRecord
from backend.app.models.repositories import UserRepository

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])

class SubmissionRequest(BaseModel):
    session_id: str
    orchestration_id: str
    learner_response: str
    attempt_number: int = 1

@router.post("/thinking")
async def submit_thinking(request: SubmissionRequest, db: Session = Depends(get_db)):
    record = db.query(ThinkingResultRecord).filter(
        ThinkingResultRecord.session_id == request.session_id,
        ThinkingResultRecord.attempt_number == request.attempt_number
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Thinking task not found for this session/attempt")

    record.learner_response = request.learner_response
    db.commit()

    return {"status": "submitted", "message": "Thinking response captured successfully"}

@router.post("/practical")
async def submit_practical(request: SubmissionRequest, db: Session = Depends(get_db)):
    record = db.query(PracticalResultRecord).filter(
        PracticalResultRecord.session_id == request.session_id,
        PracticalResultRecord.attempt_number == request.attempt_number
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Practical task not found for this session/attempt")

    record.learner_response = request.learner_response
    db.commit()

    return {"status": "submitted", "message": "Practical response captured successfully"}
