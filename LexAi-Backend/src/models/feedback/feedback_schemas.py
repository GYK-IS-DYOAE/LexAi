from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class VoteType(str, Enum):
    like = "like"
    dislike = "dislike"


class FeedbackCreate(BaseModel):
    question_id: Optional[UUID] = None
    answer_id: UUID
    question_text: str
    answer_text: str
    vote: Optional[VoteType] = None
    user_id: Optional[UUID] = None
    model: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: UUID
    question_id: Optional[UUID]
    answer_id: UUID
    question_text: str
    answer_text: str
    vote: Optional[VoteType] = None
    user_id: Optional[UUID]
    model: Optional[str]
    ts: datetime

    user_email: Optional[str] = None
    user_name: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
