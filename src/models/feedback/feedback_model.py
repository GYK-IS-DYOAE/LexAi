# src/models/feedback/feedback_model.py

from src.core.base import Base
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
import datetime

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query_id = Column(String, nullable=True)
    response_id = Column(String, nullable=True)
    vote = Column(Integer, nullable=False)  # -1 = dislike, 1 = like
    reason = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    model = Column(String, nullable=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow)

class Action(Base):
    __tablename__ = "actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day = Column(String, nullable=False)  # örnek: "2025-10-08"
    action = Column(String, nullable=False)  # örnek: "reranker_retrain"
    params = Column(JSON, nullable=True)     # örnek: {"days": 7}
    triggered = Column(Integer, default=0)
