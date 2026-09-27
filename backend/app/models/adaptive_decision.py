import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from backend.app.core.database import Base


class AdaptiveDecisionRecord(Base):
    __tablename__ = "adaptive_decisions"
    __table_args__ = (
        UniqueConstraint(
            "orchestration_id", "evaluation_id", name="uq_orchestration_evaluation_decision"
        ),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"decision_{uuid.uuid4().hex[:12]}",
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
    evaluation_id = Column(
        String,
        ForeignKey("elara_evaluations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    decision = Column(String, nullable=False)
    mastery_status = Column(String, nullable=False)
    current_difficulty = Column(String, nullable=False)
    next_difficulty = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    remediation_required = Column(Integer, nullable=False)
    decision_json = Column(Text, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
