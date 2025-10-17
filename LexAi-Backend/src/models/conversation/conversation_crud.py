from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

from src.models.conversation.session_model import ConversationSession
from src.models.conversation.message_model import Message, SenderType


def create_session(db: Session, user_id: UUID, title: str = "Yeni Sohbet"):
    session = ConversationSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_sessions(db: Session, user_id: UUID):
    return (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == user_id)
        .order_by(ConversationSession.updated_at.desc())
        .all()
    )


def get_session_by_id(db: Session, session_id: UUID, user_id: UUID):
    return (
        db.query(ConversationSession)
        .filter(
            ConversationSession.id == session_id,
            ConversationSession.user_id == user_id
        )
        .first()
    )


def get_session_messages(db: Session, session_id: UUID, user_id: UUID):
    return (
        db.query(Message)
        .join(ConversationSession, Message.session_id == ConversationSession.id)
        .filter(
            ConversationSession.id == session_id,
            ConversationSession.user_id == user_id
        )
        .order_by(Message.timestamp.asc())
        .all()
    )


def add_message(db: Session, session_id: UUID, sender: SenderType, content: str, meta_info=None):
    message = Message(
        session_id=session_id,
        sender=sender,
        content=content,
        meta_info=meta_info  # models.py'deki alan adıyla uyumlu
    )

    db.add(message)

    # updated_at güncelle
    db.query(ConversationSession).filter(
        ConversationSession.id == session_id
    ).update({"updated_at": datetime.utcnow()})

    db.commit()
    db.refresh(message)
    return message


def update_session_title(db: Session, session_id: UUID, user_id: UUID, new_title: str):
    session = (
        db.query(ConversationSession)
        .filter(
            ConversationSession.id == session_id,
            ConversationSession.user_id == user_id
        )
        .first()
    )

    if session:
        session.title = new_title
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
    return session


def delete_session(db: Session, session_id: UUID, user_id: UUID):
    session = (
        db.query(ConversationSession)
        .filter(
            ConversationSession.id == session_id,
            ConversationSession.user_id == user_id
        )
        .first()
    )

    if session:
        db.delete(session)
        db.commit()
        return True

    return False


def get_sessions_by_user(db: Session, user_id: str):
    """Kullanıcının tüm oturumlarını döner (en son oluşturulan en üstte)."""
    return (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == user_id)
        .order_by(ConversationSession.created_at.desc())
        .all()
    )


def get_last_messages(db: Session, session_id: str, limit: int = 4):
    """Belirli bir oturumun son n mesajını (sıralı şekilde) getirir."""
    from src.models.conversation.message_model import Message
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()[::-1]  # kronolojik sıraya çevir
    )
