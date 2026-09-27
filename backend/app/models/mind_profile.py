import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class MindProfile(Base):
    __tablename__ = "mind_profiles"

    id = Column(String, primary_key=True, default=lambda: f"mind_{uuid.uuid4().hex[:12]}")
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    learning_motivation = Column(String, nullable=False)
    preferred_explanation = Column(String, nullable=False)
    support_when_stuck = Column(String, nullable=False)
    feedback_preference = Column(String, nullable=False)
    challenge_preference = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="mind_profile")
