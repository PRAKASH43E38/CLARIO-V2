import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text

from backend.app.core.database import Base


class ElaraEvaluationRecord(Base):
    __tablename__ = "elara_evaluations"

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"evaluation_{uuid.uuid4().hex[:12]}",
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
    quiz_result_id = Column(
        String,
        ForeignKey("quiz_results.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    concept_name = Column(String, nullable=False)
    quiz_performance_json = Column(Text, nullable=False)
    concept_strength = Column(String, nullable=False)
    concept_weakness = Column(String, nullable=False)
    overall_evaluation = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    difficulty_signal = Column(String, nullable=False)
    evidence_summary = Column(Text, nullable=False)
    evaluation_json = Column(Text, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    evaluated_at = Column(DateTime, nullable=False)
