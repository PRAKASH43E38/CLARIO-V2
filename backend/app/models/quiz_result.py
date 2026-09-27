import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from backend.app.core.database import Base


class QuizResultRecord(Base):
    __tablename__ = "quiz_results"

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"quiz_{uuid.uuid4().hex[:12]}",
    )
    session_id = Column(
        String,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    orchestration_id = Column(
        String,
        ForeignKey("clario_orchestrations.id", ondelete="CASCADE"),
        unique=True,
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
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    submitted_at = Column(DateTime, nullable=True)
