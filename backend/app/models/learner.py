import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id = Column(String, primary_key=True, default=lambda: f"prf_{uuid.uuid4().hex[:12]}")
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    learning_goal = Column(String, nullable=False)
    current_level = Column(String, nullable=False)
    learning_preference = Column(String, nullable=False)
    interests = Column(String, nullable=False)
    initial_confidence = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="learner_profile")
    concept_performances = relationship("ConceptPerformance", back_populates="learner_profile", cascade="all, delete-orphan")

class ConceptPerformance(Base):
    __tablename__ = "concept_performances"

    id = Column(String, primary_key=True, default=lambda: f"cp_{uuid.uuid4().hex[:12]}")
    profile_id = Column(String, ForeignKey("learner_profiles.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="learning")  # learning, mastered, remediating
    difficulty_level = Column(Integer, nullable=False, default=1)
    mastery_score = Column(Float, nullable=False, default=0.0)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_assessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("profile_id", "concept_id", name="uq_profile_concept"),
    )

    learner_profile = relationship("LearnerProfile", back_populates="concept_performances")
    concept = relationship("Concept", back_populates="performances")
