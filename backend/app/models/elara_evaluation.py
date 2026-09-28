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
    Text,
    UniqueConstraint,
)

from backend.app.core.database import Base


class ElaraEvaluationRecord(Base):
    __tablename__ = "elara_evaluations"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number"),
        UniqueConstraint("orchestration_id", "attempt_number"),
        CheckConstraint(
            "concept_strength IN ('strong', 'moderate', 'weak', 'insufficient_evidence')",
            name="ck_elara_evaluation_strength",
        ),
        CheckConstraint(
            "concept_weakness IN ('none', 'conceptual', 'reasoning', 'practical', "
            "'recall', 'mixed', 'insufficient_evidence')",
            name="ck_elara_evaluation_weakness",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_elara_evaluation_confidence",
        ),
        CheckConstraint(
            "difficulty_signal IN ('increase', 'maintain', 'decrease', 'insufficient_evidence')",
            name="ck_elara_evaluation_difficulty_signal",
        ),
        CheckConstraint("attempt_number >= 1", name="ck_elara_evaluation_attempt"),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"evaluation_{uuid.uuid4().hex[:12]}",
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
    attempt_number = Column(Integer, nullable=False, default=1)
    evaluated_at = Column(DateTime(timezone=True), nullable=False)
