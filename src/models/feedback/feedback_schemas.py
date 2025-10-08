# src/models/feedback/feedback_schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional

class VoteRequest(BaseModel):
    query_id: Optional[str] = None
    response_id: Optional[str] = None
    vote: int = Field(..., description="1 for like, -1 for dislike")
    reason: Optional[str] = None
    tags: Optional[List[str]] = None
    model: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    query_id: Optional[str]
    response_id: Optional[str]
    vote: int
    reason: Optional[str]
    tags: Optional[List[str]]
    model: Optional[str]
    ts: str

    class Config:
        orm_mode = True
