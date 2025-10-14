from uuid import uuid4
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth.security import get_current_user
from src.models.auth.user_model import User
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm
from src.retrieval.retrieve_combined import hybrid_search
from src.models.feedback import feedback_crud
from src.models.feedback.feedback_schemas import FeedbackCreate
from src.core.db import SessionLocal

# ✅ Sohbet geçmişi için eklenen importlar
from src.models.conversation.conversation_crud import (
    create_session,
    add_message
)
from src.models.conversation.message_model import SenderType

router = APIRouter(tags=["RAG"])


class QueryRequest(BaseModel):
    query: str
    topn: int = 8
    session_id: str | None = None  # ✅ Opsiyonel session_id


class AskResponse(BaseModel):
    answer: str
    feedback_id: str
    session_id: str  # ✅ Frontend devam ederken lazım olacak
    message_id: str  # ✅ Son assistant mesajı


@router.post("/ask", response_model=AskResponse)
def ask(
    req: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    1. Session varsa devam eder, yoksa oluşturulur.
    2. Kullanıcının sorusu Message tablosuna kaydedilir.
    3. LLM cevabı kaydedilir.
    4. Feedback kaydı oluşturulur.
    5. message_id, session_id frontend'e döner.
    """

    db: Session = SessionLocal()

    try:
        # ✅ 1) Session yoksa oluştur
        if not req.session_id:
            session = create_session(db, user_id=current_user.id)
            session_id = session.id
        else:
            session_id = req.session_id

        # ✅ 2) Kullanıcı mesajını kaydet
        user_message = add_message(
            db=db,
            session_id=session_id,
            sender=SenderType.user,
            content=req.query
        )

        # ✅ 3) RAG workflow
        hits = hybrid_search(req.query, topn=req.topn)
        passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]

        print(f"[{current_user.email}] QUERY:", req.query)

        user_prompt = build_user_prompt(req.query, passages)
        answer = query_llm(SYSTEM_PROMPT, user_prompt)

        # ✅ 4) Assistant cevabını kaydet
        assistant_message = add_message(
            db=db,
            session_id=session_id,
            sender=SenderType.assistant,
            content=answer
        )

        # ✅ 5) Feedback kaydı (eski sistem korunarak)
        feedback_data = FeedbackCreate(
            user_id=current_user.id,
            question_id=None,
            answer_id=assistant_message.id,  # ✅ gerçek cevap id
            question_text=req.query,
            answer_text=answer,
            vote=None,
            model="qwen2.5:7b-instruct"
        )
        feedback = feedback_crud.create_feedback(db, feedback_data)

        return {
            "answer": answer,
            "feedback_id": str(feedback.id),
            "session_id": str(session_id),
            "message_id": str(assistant_message.id)
        }

    finally:
        db.close()
