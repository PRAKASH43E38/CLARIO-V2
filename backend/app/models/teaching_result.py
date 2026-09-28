import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import CheckConstraint

from backend.app.core.database import Base


class TeachingResultRecord(Base):
    __tablename__ = "teaching_results"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number"),
        UniqueConstraint("orchestration_id", "attempt_number"),
        CheckConstraint("attempt_number >= 1", name="ck_teaching_result_attempt"),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"teaching_{uuid.uuid4().hex[:12]}",
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
    concept = Column(String, nullable=False)
    response_json = Column(Text, nullable=False)
    learner_level = Column(String, nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
