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


class QuizResultRecord(Base):
    __tablename__ = "quiz_results"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number"),
        UniqueConstraint("orchestration_id", "attempt_number"),
        CheckConstraint(
            "difficulty IN ('EASY', 'MEDIUM', 'HARD')",
            name="ck_quiz_result_difficulty",
        ),
        CheckConstraint(
            "time_limit_seconds IN (30, 60, 90)",
            name="ck_quiz_result_time_limit",
        ),
        CheckConstraint(
            "status IN ('GENERATED', 'IN_PROGRESS', 'SUBMITTED')",
            name="ck_quiz_result_status",
        ),
        CheckConstraint("attempt_number >= 1", name="ck_quiz_result_attempt"),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"quiz_{uuid.uuid4().hex[:12]}",
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
    difficulty = Column(String, nullable=False)
    time_limit_seconds = Column(Integer, nullable=False)
    questions_json = Column(Text, nullable=False)
    answer_key_json = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="GENERATED")
    submitted_answers_json = Column(Text, nullable=True)
    correctness_json = Column(Text, nullable=True)
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
    submitted_at = Column(DateTime(timezone=True), nullable=True)
