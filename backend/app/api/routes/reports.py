from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.core.database import get_db
from backend.app.models.session_concept_performance import SessionConceptPerformanceRecord
from backend.app.services.gamification_service import GamificationService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

@router.get("/summary/{session_id}")
async def get_session_summary(session_id: str, db: Session = Depends(get_db)):
    """
    Aggregates performance data into a final learner report.
    """
    perf_records = db.query(SessionConceptPerformanceRecord).filter(
        SessionConceptPerformanceRecord.session_id == session_id
    ).all()

    if not perf_records:
        raise HTTPException(status_code=404, detail="No performance data found for this session")

    mastered_count = sum(1 for r in perf_records if r.mastery_status == "mastered")
    total_count = len(perf_records)
    mastery_percentage = (mastered_count / total_count) * 100 if total_count > 0 else 0

    report = {
        "session_id": session_id,
        "overall_mastery": f"{mastery_percentage:.1f}%",
        "concepts": [
            {"concept": r.concept_name, "status": r.mastery_status, "score": r.quiz_accuracy}
            for r in perf_records
        ],
        "total_xp": GamificationService.calculate_xp(db, session_id),
        "conclusion": "Excellent progress!" if mastery_percentage >= 80 else "Keep practicing!"
    }

    return report
