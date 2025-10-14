from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from src.core.base import Base
import uuid
from datetime import datetime
import enum


class SenderType(enum.Enum):
    """Mesajı kimin gönderdiğini belirtir."""
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(Base):
    """
    Oturum içindeki bireysel mesajları tutar.
    Kullanıcı ve asistan mesajları bu tabloda saklanır.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    sender = Column(Enum(SenderType, name="sender_type"), nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    meta_info = Column(JSON, nullable=True)

