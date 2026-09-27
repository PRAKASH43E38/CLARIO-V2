import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from backend.app.core.database import Base


class SessionConceptPerformanceRecord(Base):
    __tablename__ = "session_concept_performances"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "concept_id", name="uq_session_concept_performance"
        ),
        CheckConstraint(
            "mastery_status IN ('learning', 'mastered', 'remediating')",
            name="ck_session_concept_performance_status",
        ),
        CheckConstraint(
            "current_difficulty IN ('EASY', 'MEDIUM', 'HARD')",
            name="ck_session_concept_performance_difficulty",
        ),
        CheckConstraint(
            "evaluation_confidence >= 0 AND evaluation_confidence <= 1",
            name="ck_session_concept_performance_confidence",
        ),
        CheckConstraint(
            "quiz_accuracy >= 0 AND quiz_accuracy <= 100",
            name="ck_session_concept_performance_accuracy",
        ),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"scp_{uuid.uuid4().hex[:12]}",
    )
    session_id = Column(
        String,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    orchestration_id = Column(
        String,
        ForeignKey("clario_orchestrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_id = Column(
        String,
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_name = Column(String, nullable=False)
    current_difficulty = Column(String, nullable=False)
    mastery_status = Column(String, nullable=False, default="learning")
    strength = Column(String, nullable=False)
    weakness = Column(String, nullable=False)
    evaluation_confidence = Column(Float, nullable=False)
    quiz_accuracy = Column(Float, nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0)
    remediation_count = Column(Integer, nullable=False, default=0)
    last_evaluation_id = Column(
        String,
        ForeignKey("elara_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
