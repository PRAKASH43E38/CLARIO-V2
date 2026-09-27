import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class SessionInputs(Base):
    __tablename__ = "session_inputs"

    id = Column(String, primary_key=True, default=lambda: f"in_{uuid.uuid4().hex[:12]}")
    session_id = Column(String, ForeignKey("learning_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    task = Column(Text, nullable=False)
    goal = Column(Text, nullable=False)
    learner_state = Column(Text, nullable=False)
    interest = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("LearningSession", back_populates="session_inputs")
