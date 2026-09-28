import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String

from backend.app.core.database import Base


class OrchestrationRecord(Base):
    __tablename__ = "clario_orchestrations"

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"orchestration_{uuid.uuid4().hex[:12]}",
    )
    session_id = Column(
        String,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    cala_plan_id = Column(
        String,
        ForeignKey("cala_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_state = Column(String, nullable=False)
    current_step = Column(String, nullable=False)
    research_package_id = Column(
        String,
        ForeignKey("research_packages.id", ondelete="SET NULL"),
        nullable=True,
    )
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
