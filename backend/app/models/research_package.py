import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from backend.app.core.database import Base


class ResearchPackageRecord(Base):
    __tablename__ = "research_packages"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number"),
        CheckConstraint("attempt_number >= 1", name="ck_research_package_attempt"),
        Index(
            "ix_research_packages_session_level_attempt",
            "session_id",
            "level_id",
            "attempt_number",
        ),
    )

    id = Column(
        String,
        primary_key=True,
        default=lambda: f"research_{uuid.uuid4().hex[:12]}",
    )
    session_id = Column(
        String,
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_id = Column(String, nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    package_json = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
