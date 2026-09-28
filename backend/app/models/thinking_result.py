import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from backend.app.core.database import Base


class ThinkingResultRecord(Base):
    __tablename__ = "thinking_results"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number"),
        UniqueConstraint("orchestration_id", "attempt_number"),
        CheckConstraint("attempt_number >= 1", name="ck_thinking_result_attempt"),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"thinking_{uuid.uuid4().hex[:12]}",
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
    learner_response = Column(Text, nullable=True)
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
