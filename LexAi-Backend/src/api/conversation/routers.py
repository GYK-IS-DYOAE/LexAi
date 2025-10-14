# src/api/conversation/routers.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from src.api.auth.security import get_current_user
from src.core.db import SessionLocal
from src.core.deps import get_db


from src.models.conversation.conversation_crud import (
    create_session,
    get_user_sessions,
    get_session_by_id,
    get_session_messages,
    add_message,
    update_session_title,
    delete_session,
)


from src.models.conversation.conversation_schemas import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    MessageCreate,
    MessageResponse,
)


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


@router.post("/session", response_model=SessionResponse)
def create_new_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    session = create_session(db, user_id=current_user.id, title=session_data.title)
    # Pydantic v2: model_validate(..., from_attributes=True)
    return SessionResponse.model_validate(session, from_attributes=True)


@router.get("/sessions", response_model=list[SessionResponse])
def list_user_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sessions = get_user_sessions(db, user_id=current_user.id)
    return [SessionResponse.model_validate(s, from_attributes=True) for s in sessions]


@router.get("/session/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    session = get_session_by_id(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = get_session_messages(db, session_id, current_user.id)

    return SessionDetailResponse(
        **SessionResponse.model_validate(session, from_attributes=True).model_dump(),
        messages=[MessageResponse.model_validate(m, from_attributes=True) for m in messages],
    )


@router.post("/session/{session_id}/message")
def add_message_to_session(
    session_id: UUID,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    session = get_session_by_id(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Kullanıcı mesajını kaydet
    user_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.user,
        content=message_data.content,
        meta_info=message_data.meta_info,
    )

    # RAG + LLM
    hits = hybrid_search(message_data.content, topn=5)
    passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]
    user_prompt = build_user_prompt(message_data.content, passages)
    answer_text = query_llm(SYSTEM_PROMPT, user_prompt)

    # Asistan mesajını kaydet
    assistant_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.assistant,
        content=answer_text,
        meta_info=None,
    )

    # Feedback kaydı oluştur
    feedback_data = FeedbackCreate(
        user_id=current_user.id,
        question_id=user_msg.id,
        answer_id=assistant_msg.id,
        question_text=user_msg.content,
        answer_text=assistant_msg.content,
        vote=None,
        model="qwen2.5:7b-instruct",
    )
    feedback = create_feedback(db, feedback_data)

    return {
        "assistant_message": assistant_msg.content,
        "feedback_id": str(feedback.id),
    }


@router.patch("/session/{session_id}", response_model=SessionResponse)
def rename_session(
    session_id: UUID,
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
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
    ok = delete_session(db, session_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"detail": "Session deleted successfully"}
