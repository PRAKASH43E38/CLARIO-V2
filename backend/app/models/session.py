import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id = Column(String, primary_key=True, default=lambda: f"ses_{uuid.uuid4().hex[:12]}")
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="active")
    started_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="learning_sessions")
    topic = relationship(
        "Topic", back_populates="learning_sessions", foreign_keys=[topic_id]
    )
    activities = relationship("Activity", back_populates="session", cascade="all, delete-orphan")
    session_inputs = relationship("SessionInputs", back_populates="session", uselist=False, cascade="all, delete-orphan")
    cala_plan = relationship("CalaPlanRecord", uselist=False, cascade="all, delete-orphan")
    research_package = relationship("ResearchPackageRecord", uselist=False, cascade="all, delete-orphan")

class Activity(Base):
    __tablename__ = "activities"

    id = Column(String, primary_key=True, default=lambda: f"act_{uuid.uuid4().hex[:12]}")
    session_id = Column(String, ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    companion_type = Column(String, nullable=False)  # teaching, thinking, practical, quiz
    content_payload = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("LearningSession", back_populates="activities")
    concept = relationship("Concept", back_populates="activities")
    responses = relationship("LearnerResponse", back_populates="activity", cascade="all, delete-orphan")

class LearnerResponse(Base):
    __tablename__ = "learner_responses"

    id = Column(String, primary_key=True, default=lambda: f"rsp_{uuid.uuid4().hex[:12]}")
    activity_id = Column(String, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    response_text = Column(Text, nullable=False)
    submitted_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    activity = relationship("Activity", back_populates="responses")
    evaluations = relationship("Evaluation", back_populates="response", cascade="all, delete-orphan")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String, primary_key=True, default=lambda: f"evl_{uuid.uuid4().hex[:12]}")
    response_id = Column(String, ForeignKey("learner_responses.id", ondelete="CASCADE"), nullable=False)
    evaluator_name = Column(String, nullable=False)  # Ellara
    score = Column(Float, nullable=False)
    feedback_payload = Column(Text, nullable=False)
    remediation_required = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    response = relationship("LearnerResponse", back_populates="evaluations")
