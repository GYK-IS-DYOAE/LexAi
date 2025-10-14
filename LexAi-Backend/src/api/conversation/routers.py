from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from src.api.auth.security import get_db, get_current_user

# CRUD Fonksiyonları
from src.models.conversation.conversation_crud import (
    create_session,
    get_user_sessions,
    get_session_by_id,
    get_session_messages,
    add_message,
    update_session_title,
    delete_session
)

# Şema Dosyaları
from src.models.conversation.conversation_schemas import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    MessageCreate,
    MessageResponse
)

# Diğer Gereken Importlar
from src.models.conversation.message_model import SenderType
from src.retrieval.retrieve_combined import hybrid_search
from src.rag.prompt_builder import build_user_prompt, SYSTEM_PROMPT
from src.rag.query_llm import query_llm
from src.models.feedback.feedback_schemas import FeedbackCreate
from src.models.feedback.feedback_crud import create_feedback

router = APIRouter(
    prefix="/conversation",
    tags=["Conversation"],
)

# ✅ 1. Yeni oturum oluştur
@router.post("/session", response_model=SessionResponse)
def create_new_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = create_session(db, user_id=current_user.id, title=session_data.title)
    return SessionResponse.from_orm(session)

# ✅ 2. Kullanıcının tüm oturumlarını getir
@router.get("/sessions", response_model=list[SessionResponse])
def list_user_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    sessions = get_user_sessions(db, user_id=current_user.id)
    return [SessionResponse.from_orm(s) for s in sessions]

# ✅ 3. Belirli oturumun detayları (mesajlarla birlikte)
@router.get("/session/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = get_session_by_id(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = get_session_messages(db, session_id, current_user.id)

    return SessionDetailResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[MessageResponse.from_orm(msg) for msg in messages]
    )

# ✅ 4. Mesaj gönder + LLM cevabı + feedback
@router.post("/session/{session_id}/message")
def add_message_to_session(
    session_id: UUID,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = get_session_by_id(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # ✅ Kullanıcı mesajını kaydet
    user_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.user,
        content=message_data.content,
        meta_info=message_data.meta_info
    )

    # ✅ RAG + LLM cevabını üret
    hits = hybrid_search(message_data.content, topn=5)
    passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]
    user_prompt = build_user_prompt(message_data.content, passages)
    answer_text = query_llm(SYSTEM_PROMPT, user_prompt)

    # ✅ Asistan mesajını kaydet
    assistant_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.assistant,
        content=answer_text,
        meta_info=None
    )

    # ✅ Feedback kaydı oluştur
    feedback_data = FeedbackCreate(
        user_id=current_user.id,
        question_id=user_msg.id,
        answer_id=assistant_msg.id,
        question_text=user_msg.content,
        answer_text=assistant_msg.content,
        vote=None,
        model="qwen2.5:7b-instruct"
    )
    feedback = create_feedback(db, feedback_data)

    return {
        "assistant_message": assistant_msg.content,
        "feedback_id": str(feedback.id)
    }

# ✅ 5. Oturum adını güncelle
@router.patch("/session/{session_id}", response_model=SessionResponse)
def rename_session(
    session_id: UUID,
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    updated = update_session_title(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        new_title=data.title
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionResponse.from_orm(updated)

# ✅ 6. Oturumu sil
@router.delete("/session/{session_id}")
def remove_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = delete_session(db, session_id, current_user.id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return {"detail": "Session deleted successfully"}
