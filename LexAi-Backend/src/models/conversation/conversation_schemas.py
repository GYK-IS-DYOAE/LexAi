from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum


# ✅ Sender ENUM (DB ile tutarlı)
class SenderType(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


# ✅ Mesaj oluşturma (request body)
class MessageCreate(BaseModel):
    content: str
    meta_info: Optional[dict] = None  # meta_info yerine metadata kullanılıyor


# ✅ Mesaj dönen model (response)
class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    sender: SenderType
    content: str
    timestamp: datetime
    meta_info: Optional[dict] = None  # Model ile uyumlu alan adı

    class Config:
        orm_mode = True  # ✅ DÜZELTİLDİ


# ✅ Yeni session oluşturma
class SessionCreate(BaseModel):
    title: Optional[str] = "Yeni Sohbet"


# ✅ Session listesi dönerken kullanılan model
class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True  # ✅ DÜZELTİLDİ


# ✅ Mesajlı session detayı için model
class SessionDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]

    class Config:
        orm_mode = True  # ✅ DÜZELTİLDİ
