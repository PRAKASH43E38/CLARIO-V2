import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from backend.app.core.database import Base


class PracticalResultRecord(Base):
    __tablename__ = "practical_results"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number"),
        UniqueConstraint("orchestration_id", "attempt_number"),
        CheckConstraint("attempt_number >= 1", name="ck_practical_result_attempt"),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"practical_{uuid.uuid4().hex[:12]}",
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
    scenario = Column(Text, nullable=False)
    practical_task = Column(Text, nullable=False)
    real_world_context = Column(Text, nullable=False)
    expected_action = Column(Text, nullable=False)
    success_criteria = Column(Text, nullable=False)
    difficulty = Column(String, nullable=False)
    research_source_ids = Column(Text, nullable=False)
    learner_response = Column(Text, nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
