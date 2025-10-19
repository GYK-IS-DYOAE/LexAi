from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging, re

from src.api.auth.security import get_current_user
from src.core.deps import get_db
from src.models.auth.user_model import User
from src.retrieval.retrieve_combined import hybrid_search
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm
from src.rag.config import MAX_TOTAL_PASSAGES, LLM_MODEL_NAME
from src.user_input.query_service import process_user_query
from src.models.feedback import feedback_crud
from src.models.feedback.feedback_schemas import FeedbackCreate
from src.models.conversation.conversation_crud import (
    create_session, add_message, get_last_messages, get_session_by_id,
)
from src.models.conversation.message_model import SenderType

router = APIRouter(tags=["RAG"])
logger = logging.getLogger("uvicorn.error")


def extract_topic(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    keywords = []
    if "nafaka" in text: keywords.append("nafaka")
    if "boşan" in text: keywords.append("boşanma")
    if "miras" in text: keywords.append("miras paylaşımı")
    if "arsa" in text or "ortak" in text: keywords.append("ortak mülkiyet")
    if "tazminat" in text: keywords.append("tazminat")
    if "borç" in text: keywords.append("borç ilişkisi")
    if "kira" in text: keywords.append("kira sözleşmesi")
    if "iş" in text and "çıkar" in text: keywords.append("işten çıkarma")
    if not keywords:
        tokens = re.findall(r"\b[a-zçğıöşü]{4,}\b", text)
        keywords.extend(tokens[:3])
    return " ".join(sorted(set(keywords)))


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


@router.post("/ask", response_model=AskResponse)
def ask(
    req: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cleaned_query, precomputed_answer = process_user_query(req.query)

    if not req.session_id:
        session = create_session(db, user_id=current_user.id, title="Yeni Sohbet")
        session_id = str(session.id)
    else:
        existing = get_session_by_id(db, req.session_id, current_user.id)
        session_id = str(existing.id) if existing else str(
            create_session(db, user_id=current_user.id, title="Yeni Sohbet").id
        )

    user_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.user,
        content=cleaned_query,
        meta_info={"raw_query": req.query},
    )

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

    history_msgs = get_last_messages(db, session_id=session_id, limit=6)
    conversation_history = [
        {"user": m.content} if m.sender == SenderType.user else {"assistant": m.content}
        for m in history_msgs
    ]

    recent_user_msgs = [m.content for m in history_msgs if m.sender == SenderType.user]
    recent_context = " ".join(recent_user_msgs[-3:]).strip()
    context_topic = extract_topic(recent_context)
    query_topic = extract_topic(cleaned_query)

    if context_topic and context_topic in query_topic:
        context_query = f"{context_topic} {cleaned_query}"
    elif context_topic and not any(w in cleaned_query for w in context_topic.split()):
        context_query = f"{context_topic} {cleaned_query}"
    else:
        context_query = cleaned_query

    topn = max(1, min(req.topn, 20))
    hits = hybrid_search(context_query, topn=topn)

    seen, passages = set(), []
    for h in hits:
        if h.doc_id in seen:
            continue
        payload = dict(h.payload or {})
        payload["doc_id"] = h.doc_id
        full_txt = (
            payload.get("karar_metni")
            or payload.get("karar_metni_meta")
            or payload.get("karar_metni_raw")
            or getattr(h, "text_full", None)
            or ""
        ).strip()
        if not full_txt:
            continue
        payload["karar_metni"] = full_txt
        payload["dava_turu"] = payload.get("dava_turu") or payload.get("dava_turu_norm") or ""
        payload["karar"] = payload.get("karar") or payload.get("sonuc") or ""
        payload["karar_preview"] = payload.get("karar_preview") or full_txt[:300]
        passages.append(payload)
        seen.add(h.doc_id)
        if len(passages) >= MAX_TOTAL_PASSAGES:
            break

    if not passages:
        raise HTTPException(status_code=404, detail="İlgili karar metni bulunamadı.")

    up_out = build_user_prompt(cleaned_query, passages, conversation_history)
    user_prompt, early_answer = up_out if isinstance(up_out, tuple) else (up_out, None)

    if early_answer:
        assistant_msg = add_message(
            db=db, session_id=session_id, sender=SenderType.assistant, content=early_answer
        )
        fb = feedback_crud.create_feedback(
            db,
            FeedbackCreate(
                user_id=current_user.id,
                question_id=user_msg.id,
                answer_id=assistant_msg.id,
                question_text=cleaned_query,
                answer_text=early_answer,
                vote=None,
                model="rule-based",
            ),
        )
        return AskResponse(
            question=cleaned_query,
            answer=early_answer,
            question_id=str(user_msg.id),
            answer_id=str(assistant_msg.id),
            feedback_id=str(fb.id),
            session_id=session_id,
        )

    ans, _ = query_llm(
        SYSTEM_PROMPT,
        user_prompt,
        return_prompt=True,
        num_ctx=16384,
        num_predict=1024,
    )

    assistant_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.assistant,
        content=ans,
        meta_info={"model": "llama3:8b", "passage_count": len(passages)},
    )

    fb = feedback_crud.create_feedback(
        db,
        FeedbackCreate(
            user_id=current_user.id,
            question_id=user_msg.id,
            answer_id=assistant_msg.id,
            question_text=cleaned_query,
            answer_text=ans,
            vote=None,
            model=LLM_MODEL_NAME,
        ),
    )

    return AskResponse(
        question=cleaned_query,
        answer=ans,
        question_id=str(user_msg.id),
        answer_id=str(assistant_msg.id),
        feedback_id=str(fb.id),
        session_id=session_id,
    )
