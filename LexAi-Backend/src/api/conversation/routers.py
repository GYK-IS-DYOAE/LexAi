# src/api/conversation/routers.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.models.conversation.conversation_crud import get_sessions_by_user
from src.models.auth.user_model import User
from uuid import UUID
from typing import Optional


from src.api.auth.security import get_current_user
from src.core.deps import get_db

from src.models.conversation.conversation_crud import (
    create_session,
    get_user_sessions,
    get_session_by_id,
    get_session_messages,
    update_session_title,
    delete_session,
)

from src.models.conversation.conversation_schemas import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    MessageResponse,
)

from src.models.feedback.feedback_crud import get_feedback_by_message_id

router = APIRouter(
    prefix="/conversation",
    tags=["Conversation"],
)


@router.post("/session", response_model=SessionResponse)
def create_new_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Yeni sohbet oturumu oluşturur."""
    session = create_session(db, user_id=current_user.id, title=session_data.title)
    return SessionResponse.model_validate(session, from_attributes=True)


@router.get("/sessions", response_model=list[SessionResponse])
def list_user_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Kullanıcının tüm sohbetlerini döner."""
    sessions = get_user_sessions(db, user_id=current_user.id)
    return [SessionResponse.model_validate(s, from_attributes=True) for s in sessions]


@router.get("/session/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Bir session'a ait tüm mesajları ve varsa feedback (vote) bilgilerini döner."""
    session = get_session_by_id(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Mesajları al
    messages = get_session_messages(db, session_id, current_user.id)

    # Her mesaj için feedback durumunu (like/dislike/null) ekle
    message_responses = []
    for m in messages:
        feedback = get_feedback_by_message_id(db, m.id)
        vote = feedback.vote if feedback else None
        feedback_id = str(feedback.id) if feedback else None  # ✅ eklendi

        message_responses.append(
            MessageResponse(
                id=m.id,
                session_id=m.session_id,
                sender=m.sender,
                content=m.content,
                timestamp=m.timestamp,
                meta_info=m.meta_info,
                vote=vote,
                feedback_id=feedback_id,  
            )
        )
    return SessionDetailResponse(
        **SessionResponse.model_validate(session, from_attributes=True).model_dump(),
        messages=message_responses,
    )


@router.patch("/session/{session_id}", response_model=SessionResponse)
def rename_session(
    session_id: UUID,
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sohbet başlığını günceller."""
    updated = update_session_title(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        new_title=data.title,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return SessionResponse.model_validate(updated, from_attributes=True)


@router.delete("/session/{session_id}")
def remove_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Belirli bir sohbet oturumunu siler."""
    ok = delete_session(db, session_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"detail": "Session deleted successfully"}


@router.get("/list", summary="Kullanıcının tüm sohbet oturumlarını döner")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Kullanıcının tüm conversation oturumlarını getirir.
    """
    sessions = get_sessions_by_user(db, current_user.id)
    return [
        {
            "id": str(s.id),
            "title": s.title or "Yeni Sohbet",
            "created_at": s.created_at,
        }
        for s in sessions
    ]