import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Topic(Base):
    __tablename__ = "topics"

    id = Column(String, primary_key=True, default=lambda: f"top_{uuid.uuid4().hex[:12]}")
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    sequence_order = Column(Integer, nullable=False, default=1)
    owner_session_id = Column(
        String, ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=True
    )

    concepts = relationship("Concept", back_populates="topic", cascade="all, delete-orphan")
    learning_sessions = relationship(
        "LearningSession",
        back_populates="topic",
        foreign_keys="LearningSession.topic_id",
    )

class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String, primary_key=True, default=lambda: f"cpt_{uuid.uuid4().hex[:12]}")
    topic_id = Column(String, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    base_difficulty = Column(Integer, nullable=False, default=1)
    sequence_order = Column(Integer, nullable=False, default=1)

    topic = relationship("Topic", back_populates="concepts")
    performances = relationship("ConceptPerformance", back_populates="concept", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="concept")
