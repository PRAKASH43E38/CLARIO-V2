from sqlalchemy.orm import Session
from backend.app.models.session_concept_performance import SessionConceptPerformanceRecord as SessionConceptPerformance
from backend.app.models.cala_plan import CalaPlanRecord

class CurriculumManager:
    @staticmethod
    def check_level_completion(db: Session, session_id: str, level: int) -> bool:
        """
        Checks if all concepts for a given level in a session are mastered.
        """
        # Get all concepts mapped to this level for the session
        plan = CalaPlanRecord.get_by_session_id(db, session_id)
        if not plan:
            return False

        # In our simplified model, we check if every concept required for the current
        # level has a performance record marked as 'MASTERED'
        level_key = f"level_{level}"
        concepts_to_check = plan.roadmap.get(level_key, [])

        if not concepts_to_check:
            return False

        for concept in concepts_to_check:
            perf = db.query(SessionConceptPerformance).filter(
                SessionConceptPerformance.session_id == session_id,
                SessionConceptPerformance.concept == concept
            ).first()

            if not perf or perf.status != "MASTERED":
                return False

        return True

    @staticmethod
    def unlock_next_level(db: Session, session_id: str, current_level: int):
        """
        Handles the logic of transitioning the session to the next level.
        """
        if CurriculumManager.check_level_completion(db, session_id, current_level):
            next_level = current_level + 1
            # Update session state or plan to unlock next level
            # For simplicity, we return True to signal the orchestrator to advance
            return True
        return False
