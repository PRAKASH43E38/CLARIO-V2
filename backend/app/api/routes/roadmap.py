from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.api.schemas import RoadmapResponse, RoadmapItem, ErrorResponse
from backend.app.core.database import get_db
from backend.app.cala.schemas import CalaResult
from backend.app.models.cala_plan import CalaPlanRecord
from backend.app.models.session import LearningSession
from backend.app.models.repositories import (
    UserRepository,
    LearnerProfileRepository,
    ConceptPerformanceRepository,
    CurriculumRepository,
    SessionConceptPerformanceRepository,
)
from backend.app.models.curriculum import Concept

router = APIRouter(prefix="/api/v1", tags=["roadmap"])


@router.get("/roadmap", response_model=RoadmapResponse, responses={404: {"model": ErrorResponse}})
async def get_roadmap(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    profile = LearnerProfileRepository.get_by_user_id(db, user.id)

    sessions = (
        db.query(LearningSession)
        .filter(LearningSession.user_id == user.id)
        .order_by(LearningSession.started_at.desc())
        .all()
    )
    for session in sessions:
        plan_record = (
            db.query(CalaPlanRecord)
            .filter(CalaPlanRecord.session_id == session.id)
            .first()
        )
        if not plan_record:
            continue
        plan = CalaResult.model_validate_json(plan_record.plan_json)
        active_level = next(
            (
                level
                for level in plan.roadmap
                if level.level_id
                == (plan.current_level_id or plan.recommended_starting_level)
            ),
            None,
        )
        if active_level is None:
            continue
        performances = {
            item.concept_id: item
            for item in SessionConceptPerformanceRepository.list_by_session_id(
                db, session.id
            )
        }
        flattened = []
        for level in sorted(plan.roadmap, key=lambda item: item.order):
            for topic in sorted(level.topics, key=lambda item: item.order):
                for concept in sorted(topic.concepts, key=lambda item: item.order):
                    performance = performances.get(concept.concept_id)
                    mastered = bool(
                        performance and performance.mastery_status == "mastered"
                    )
                    flattened.append(
                        RoadmapItem(
                            concept_id=concept.concept_id,
                            concept_title=concept.title,
                            status=(
                                "mastered"
                                if mastered
                                else "learning"
                                if level.level_id == active_level.level_id
                                else "upcoming"
                            ),
                            difficulty=(
                                {"EASY": 1, "MEDIUM": 3, "HARD": 5}.get(
                                    performance.current_difficulty, 1
                                )
                                if performance
                                else 1
                            ),
                            is_next=concept.concept_id == plan.active_concept_id,
                        )
                    )
        return RoadmapResponse(
            current_topic=active_level.topics[0].title
            if active_level.topics
            else active_level.title,
            topic_id=active_level.topics[0].topic_id
            if active_level.topics
            else "",
            roadmap=flattened,
            levels=[level.model_dump(mode="json") for level in plan.roadmap],
            current_level_id=active_level.level_id,
            active_concept_id=plan.active_concept_id,
        )
    
    topics = [
        topic
        for topic in CurriculumRepository.list_topics(db)
        if topic.owner_session_id is None
    ]
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