from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SQLEnum
from enum import Enum as PyEnum
import uuid
import datetime
from src.core.base import Base


class VoteType(str, PyEnum):
    like = "like"
    dislike = "dislike"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    question_id = Column(UUID(as_uuid=True), nullable=True)
    answer_id = Column(UUID(as_uuid=True), nullable=False)

    question_text = Column(String, nullable=False)
    answer_text = Column(String, nullable=False)

    vote = Column(SQLEnum(VoteType, name="vote_type"), nullable=False)

    model = Column(String, nullable=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow)
