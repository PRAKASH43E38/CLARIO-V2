import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from backend.app.core.database import Base


class CalaPlanRecord(Base):
    __tablename__ = "cala_plans"

    id = Column(String, primary_key=True, default=lambda: f"cala_{uuid.uuid4().hex[:12]}")
    session_id = Column(
        String,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    plan_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
