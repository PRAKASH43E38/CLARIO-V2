import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from backend.app.core.database import Base


class AdaptiveExecutionRecord(Base):
    __tablename__ = "clario_adaptive_executions"
    __table_args__ = (
        UniqueConstraint("decision_id"),
        UniqueConstraint("session_id", "concept_id", "attempt_number"),
        CheckConstraint("attempt_number >= 1", name="ck_adaptive_execution_attempt"),
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'AWAITING_SUBMISSION', 'COMPLETED', "
            "'FAILED', 'LIMIT_REACHED')",
            name="ck_adaptive_execution_status",
        ),
        Index(
            "ix_clario_adaptive_executions_session_created",
            "session_id",
            "created_at",
        ),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"execution_{uuid.uuid4().hex[:12]}",
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
    decision_id = Column(
        String,
        ForeignKey("adaptive_decisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_evaluation_id = Column(
        String,
        ForeignKey("elara_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number = Column(Integer, nullable=False)
    decision_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    remediation_context_json = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
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
