from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.core.base import Base
import uuid
from datetime import datetime


class ConversationSession(Base):
    """
    Kullanıcının başlattığı sohbet oturumlarını tutar.
    Örn: "İşe iade davası kıdem tazminatı"
    """
    __tablename__ = "conversation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False, default="Yeni Sohbet")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
