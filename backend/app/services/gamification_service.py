from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.models.learner import LearnerProfile

class GamificationService:
    @staticmethod
    def award_badge(db: Session, user_id: str, badge_name: str):
        """
        Simple badge awarding logic.
        Since we are avoiding complexity, we can log this in the LearnerProfile
        or a simple text field for now.
        """
        profile = LearnerProfile.get_by_user_id(db, user_id)
        if profile:
            # Assume basic_details or a similar field stores earned achievements
            current_badges = profile.basic_details or ""
            if badge_name not in current_badges:
                updated_badges = f"{current_badges}\nBadge: {badge_name}".strip()
                profile.basic_details = updated_badges
                db.commit()
                return True
        return False

    @staticmethod
    def calculate_xp(db: Session, session_id: str) -> int:
        """
        Calculates total XP based on mastered concepts in a session.
        """
        from backend.app.models.session_concept_performance import SessionConceptPerformance
        mastered = db.query(SessionConceptPerformance).filter(
            SessionConceptPerformance.session_id == session_id,
            SessionConceptPerformance.status == "MASTERED"
        ).count()
        return mastered * 100 # 100 XP per concept
