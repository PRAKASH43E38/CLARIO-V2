from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.api.schemas import DashboardResponse, ConceptBreakdownItem, ErrorResponse
from backend.app.core.database import get_db
from backend.app.models.repositories import UserRepository, LearnerProfileRepository, ConceptPerformanceRepository, CurriculumRepository
from backend.app.models.learner import LearnerProfile, ConceptPerformance
from backend.app.models.curriculum import Concept

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse, responses={404: {"model": ErrorResponse}})
async def get_dashboard(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    if not profile:
        topics = CurriculumRepository.list_topics(db)
        return DashboardResponse(
            learner_name=user.name or user.email.split("@")[0],
            current_topic=topics[0].title if topics else "",
            concept_breakdown=[],
            weak_concepts=[],
            recommended_action="Start a new learning session.",
        )
    
    performances = ConceptPerformanceRepository.list_by_profile(db, profile.id)
    
    concept_breakdown = []
    weak_concepts = []
    mastered_count = 0
    total_concepts = len(performances)
    
    for perf in performances:
        concept = db.query(Concept).filter(Concept.id == perf.concept_id).first()
        if concept:
            concept_breakdown.append(ConceptBreakdownItem(
                concept=concept.title,
                status=perf.status,
                difficulty=perf.difficulty_level,
                mastery_score=perf.mastery_score
            ))
            if perf.status in ["remediating", "learning"] and perf.mastery_score < 80:
                weak_concepts.append(concept.title)
            if perf.status == "mastered":
                mastered_count += 1
    
    current_topic = "Decision Trees"
    if performances:
        first_concept = db.query(Concept).filter(Concept.id == performances[0].concept_id).first()
        if first_concept and first_concept.topic:
            current_topic = first_concept.topic.title
    
    overall_clarity = 0
    if total_concepts > 0:
        overall_clarity = int((mastered_count / total_concepts) * 100)
    
    recommended_action = "Continue learning"
    if weak_concepts:
        recommended_action = f"Targeted remediation on {', '.join(weak_concepts)} with Teaching Friend"
    elif mastered_count == total_concepts and total_concepts > 0:
        recommended_action = "Topic completed. Advance to next topic."
    
    return DashboardResponse(
        learner_name=user.email.split("@")[0],
        current_topic=current_topic,
        concept_breakdown=concept_breakdown,
        weak_concepts=weak_concepts,
        recommended_action=recommended_action
    )