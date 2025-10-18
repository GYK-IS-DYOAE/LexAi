from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth.security import get_current_user
from src.core.deps import get_db
from src.models.auth.user_model import User

# 🔹 RAG pipeline bileşenleri
from src.retrieval.retrieve_combined import hybrid_search
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm

# 🔹 Yardımcı servisler
from src.user_input.query_service import process_user_query
from src.models.feedback import feedback_crud
from src.models.feedback.feedback_schemas import FeedbackCreate
from src.models.conversation.conversation_crud import (
    create_session,
    add_message,
    get_last_messages,
    get_session_by_id,
)
from src.models.conversation.message_model import SenderType


router = APIRouter(tags=["RAG"])


# ==================== Request / Response ====================

class QueryRequest(BaseModel):
    query: str
    topn: int = 8
    session_id: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    question_id: str
    answer_id: str
    feedback_id: str
    session_id: str


# ==================== Endpoint ====================

@router.post("/ask", response_model=AskResponse, summary="LLM üzerinden RAG cevabı üret")
def ask(
    req: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔹 RAG pipeline üzerinden LLM yanıtı üretir.
    - Kullanıcı girişini temizler (process_user_query)
    - Hibrit arama (Qdrant + OpenSearch) ile benzer karar_metni'leri bulur
    - Bu karar metinlerinden bağlam prompt'u oluşturur
    - LLM yanıtı üretir (Qwen 2.5)
    - Hem mesaj hem feedback kayıtlarını oluşturur
    """

    # 1️⃣ Sorguyu ön işle (regex + temizlik + rule-based cevap varsa yakala)
    cleaned_query, precomputed_answer = process_user_query(req.query)

    # 2️⃣ Sohbet oturumunu al / oluştur
    if not req.session_id:
        session = create_session(db, user_id=current_user.id, title="Yeni Sohbet")
        session_id = str(session.id)
    else:
        existing = get_session_by_id(db, req.session_id, current_user.id)
        session_id = str(existing.id) if existing else str(create_session(db, user_id=current_user.id, title="Yeni Sohbet").id)

    # 3️⃣ Kullanıcı mesajını kaydet
    user_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.user,
        content=cleaned_query,
        meta_info={"raw_query": req.query},
    )

    # 4️⃣ Eğer precomputed cevap varsa, direkt dön
    if precomputed_answer:
        assistant_msg = add_message(
            db=db,
            session_id=session_id,
            sender=SenderType.assistant,
            content=precomputed_answer,
            meta_info={"reason": "precomputed_from_query_service"},
        )

        fb = feedback_crud.create_feedback(
            db,
            FeedbackCreate(
                user_id=current_user.id,
                question_id=user_msg.id,
                answer_id=assistant_msg.id,
                question_text=cleaned_query,
                answer_text=precomputed_answer,
                vote=None,
                model="rule-based",
            ),
        )

        return AskResponse(
            question=cleaned_query,
            answer=precomputed_answer,
            question_id=str(user_msg.id),
            answer_id=str(assistant_msg.id),
            feedback_id=str(fb.id),
            session_id=session_id,
        )

    # 5️⃣ Hibrit arama (tam karar metinlerini al)
    topn = max(1, min(req.topn, 20))
    hits = hybrid_search(cleaned_query, topn=topn)

    # 🔹 Karar metinlerini doğrudan kullan
    passages = [
        {
            "doc_id": h.doc_id,
            "karar_metni": h.payload.get("karar_metni_meta") or h.payload.get("karar_metni_raw") or h.text_full or ""
        }
        for h in hits if (h.payload.get("karar_metni_meta") or h.payload.get("karar_metni_raw"))
    ]

    if not passages:
        raise HTTPException(status_code=404, detail="İlgili karar metni bulunamadı.")

    # 6️⃣ Önceki mesajlardan bağlam oluştur
    history_msgs = get_last_messages(db, session_id=session_id, limit=6)
    conversation_history = [
        {"user": m.content} if m.sender == SenderType.user else {"assistant": m.content}
        for m in history_msgs
    ]

    # 7️⃣ LLM için prompt oluştur
    user_prompt = build_user_prompt(cleaned_query, passages, conversation_history)

    # 8️⃣ LLM’den yanıt al
    answer = query_llm(SYSTEM_PROMPT, user_prompt)

    # 9️⃣ Asistan cevabını kaydet
    assistant_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.assistant,
        content=answer,
    )

    # 🔟 Feedback kaydı oluştur
    fb = feedback_crud.create_feedback(
        db,
        FeedbackCreate(
            user_id=current_user.id,
            question_id=user_msg.id,
            answer_id=assistant_msg.id,
            question_text=cleaned_query,
            answer_text=answer,
            vote=None,
            model="qwen2.5:7b-instruct",
        ),
    )

    # ✅ Sonuç döndür
    return AskResponse(
        question=cleaned_query,
        answer=answer,
        question_id=str(user_msg.id),
        answer_id=str(assistant_msg.id),
        feedback_id=str(fb.id),
        session_id=session_id,
    )
