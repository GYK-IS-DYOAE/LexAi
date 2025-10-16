from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SenderType(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageCreate(BaseModel):
    content: str
    meta_info: Optional[dict] = None


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    sender: SenderType
    content: str
    timestamp: datetime          
    meta_info: Optional[dict] = None
    vote: Optional[str] = None
    feedback_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionCreate(BaseModel):
    title: Optional[str] = "Yeni Sohbet"


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionDetailResponse(SessionResponse):
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
