from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.api.schemas import RoadmapResponse, RoadmapItem, ErrorResponse
from backend.app.core.database import get_db
from backend.app.models.repositories import UserRepository, LearnerProfileRepository, ConceptPerformanceRepository, CurriculumRepository
from backend.app.models.curriculum import Concept

router = APIRouter(prefix="/api/v1", tags=["roadmap"])


@router.get("/roadmap", response_model=RoadmapResponse, responses={404: {"model": ErrorResponse}})
async def get_roadmap(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    profile = LearnerProfileRepository.get_by_user_id(db, user.id)
    
    topics = CurriculumRepository.list_topics(db)
    if not topics:
        return RoadmapResponse(current_topic="", topic_id="", roadmap=[])
    
    current_topic = topics[0]
    concepts = CurriculumRepository.list_concepts_by_topic(db, current_topic.id)
    
    performances = (
        ConceptPerformanceRepository.list_by_profile(db, profile.id)
        if profile
        else []
    )
    perf_map = {p.concept_id: p for p in performances}
    
    roadmap = []
    found_next = False
    
    for concept in concepts:
        perf = perf_map.get(concept.id)
        status_val = perf.status if perf else "learning"
        difficulty = perf.difficulty_level if perf else concept.base_difficulty
        
        is_next = False
        if not found_next and status_val != "mastered":
            is_next = True
            found_next = True
        
        roadmap.append(RoadmapItem(
            concept_id=concept.id,
            concept_title=concept.title,
            status=status_val,
            difficulty=difficulty,
            is_next=is_next
        ))
    
    return RoadmapResponse(
        current_topic=current_topic.title,
        topic_id=current_topic.id,
        roadmap=roadmap
    )