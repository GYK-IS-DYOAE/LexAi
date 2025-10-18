from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

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

    # session
    if not req.session_id:
        session = create_session(db, user_id=current_user.id, title="Yeni Sohbet")
        session_id = str(session.id)
    else:
        existing = get_session_by_id(db, req.session_id, current_user.id)
        session_id = str(existing.id) if existing else str(create_session(db, user_id=current_user.id, title="Yeni Sohbet").id)

    # user msg
    user_msg = add_message(
        db=db, session_id=session_id, sender=SenderType.user,
        content=cleaned_query, meta_info={"raw_query": req.query},
    )

    if precomputed_answer:
        assistant_msg = add_message(
            db=db, session_id=session_id, sender=SenderType.assistant,
            content=precomputed_answer, meta_info={"reason": "precomputed_from_query_service"},
        )
        fb = feedback_crud.create_feedback(
            db, FeedbackCreate(
                user_id=current_user.id, question_id=user_msg.id, answer_id=assistant_msg.id,
                question_text=cleaned_query, answer_text=precomputed_answer, vote=None, model="rule-based",
            ),
        )
        return AskResponse(
            question=cleaned_query, answer=precomputed_answer,
            question_id=str(user_msg.id), answer_id=str(assistant_msg.id),
            feedback_id=str(fb.id), session_id=session_id,
        )

    # hybrid search → passages
    topn = max(1, min(req.topn, 20))
    hits = hybrid_search(cleaned_query, topn=topn)

    seen, passages = set(), []
    for h in hits:
        if h.doc_id in seen: 
            continue
        full_txt = (
            h.payload.get("karar_metni_meta")
            or h.payload.get("karar_metni_raw")
            or getattr(h, "text_full", None)
            or ""
        )
        if full_txt:
            passages.append({"doc_id": h.doc_id, "karar_metni": full_txt})
            seen.add(h.doc_id)
        if len(passages) >= MAX_TOTAL_PASSAGES:
            break

    if not passages:
        raise HTTPException(status_code=404, detail="İlgili karar metni bulunamadı.")

    # history
    history_msgs = get_last_messages(db, session_id=session_id, limit=6)
    conversation_history = [
        {"user": m.content} if m.sender == SenderType.user else {"assistant": m.content}
        for m in history_msgs
    ]

    # build prompt (tuple veya str)
    up_out = build_user_prompt(cleaned_query, passages, conversation_history)
    if isinstance(up_out, tuple):
        user_prompt, early_answer = up_out
        if early_answer:
            assistant_msg = add_message(db=db, session_id=session_id, sender=SenderType.assistant, content=early_answer)
            fb = feedback_crud.create_feedback(
                db, FeedbackCreate(
                    user_id=current_user.id, question_id=user_msg.id, answer_id=assistant_msg.id,
                    question_text=cleaned_query, answer_text=early_answer, vote=None, model="rule-based",
                ),
            )
            return AskResponse(
                question=cleaned_query, answer=early_answer,
                question_id=str(user_msg.id), answer_id=str(assistant_msg.id),
                feedback_id=str(fb.id), session_id=session_id,
            )
    else:
        user_prompt = up_out

    # >>> KESİN LOG: LLM ÖNCESİ USER_PROMPT'U YAZ <<<
    print("\n===== USER_PROMPT (PRE-LLM) BEGIN =====\n", flush=True)
    print(user_prompt, flush=True)
    print("\n===== USER_PROMPT (PRE-LLM) END =====\n", flush=True)
    logger.info("user_prompt_len=%d | passages=%d", len(user_prompt), len(passages))
    if passages:
        logger.info("first_passage_snippet=%s", (passages[0]['karar_metni'][:300].replace("\n", " ")))

    # LLM
    try:
        ans, full_prompt = query_llm(
            SYSTEM_PROMPT,
            user_prompt,
            return_prompt=True,
            num_ctx=16384,
            num_predict=1024,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM isteği başarısız: {e}")

    # >>> KESİN LOG: FULL PROMPT'U YAZ (yoksa kendimiz birleştirip yaz) <<<
    if full_prompt:
        print("\n===== LLM FULL_PROMPT BEGIN =====\n", flush=True)
        print(full_prompt, flush=True)
        print("\n===== LLM FULL_PROMPT END =====\n", flush=True)
        logger.info("full_prompt_len=%d", len(full_prompt))
    else:
        merged = f"<SYSTEM>\n{SYSTEM_PROMPT}\n</SYSTEM>\n\n<USER>\n{user_prompt}\n</USER>"
        print("\n===== LLM FULL_PROMPT (FALLBACK) BEGIN =====\n", flush=True)
        print(merged, flush=True)
        print("\n===== LLM FULL_PROMPT (FALLBACK) END =====\n", flush=True)
        logger.info("full_prompt_fallback_len=%d", len(merged))

    # save assistant message
    assistant_msg = add_message(
        db=db, session_id=session_id, sender=SenderType.assistant, content=ans,
        meta_info={"model": "qwen2.5:7b-instruct", "passage_count": len(passages)},
    )

    fb = feedback_crud.create_feedback(
        db, FeedbackCreate(
            user_id=current_user.id, question_id=user_msg.id, answer_id=assistant_msg.id,
            question_text=cleaned_query, answer_text=ans, vote=None, model=LLM_MODEL_NAME,
        ),
    )

    return AskResponse(
        question=cleaned_query, answer=ans,
        question_id=str(user_msg.id), answer_id=str(assistant_msg.id),
        feedback_id=str(fb.id), session_id=session_id,
    )
