from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth.security import get_current_user
from src.core.deps import get_db            
from src.models.auth.user_model import User
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm
from src.retrieval.retrieve_combined import hybrid_search
from src.models.feedback import feedback_crud
from src.models.feedback.feedback_schemas import FeedbackCreate
from src.user_input.query_service import process_user_query
from src.models.conversation.conversation_crud import create_session, add_message
from src.models.conversation.message_model import SenderType

router = APIRouter(tags=["RAG"])

class QueryRequest(BaseModel):
    query: str
    topn: int = 8
    session_id: str | None = None

class AskResponse(BaseModel):
    answer: str
    feedback_id: str
    session_id: str
    message_id: str

@router.post("/ask", response_model=AskResponse)
def ask(
    req: QueryRequest,
    db: Session = Depends(get_db),                 
    current_user: User = Depends(get_current_user)
):
    """ 
    1. Session varsa devam eder, yoksa oluşturulur. 
    2. Kullanıcının sorusu Message tablosuna kaydedilir. 
    3. LLM cevabı kaydedilir. 
    4. Feedback kaydı oluşturulur. 
    5. message_id, session_id frontend'e döner. 
    """
    
    # 0) Kullanıcı sorgusunu temizle/normalleştir
    cleaned_query, precomputed_answer = process_user_query(req.query)

    # 1) Session hazırla (yoksa oluştur)
    if not req.session_id:
        session = create_session(db, user_id=current_user.id, title="Yeni Sohbet")
        session_id = session.id
    else:
        session_id = req.session_id

    # 2) Kullanıcı mesajını kaydet (raw metni meta_info’ya koy, içerik cleaned)
    user_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.user,
        content=cleaned_query,
        meta_info={"raw_query": req.query}
    )

    # 3) Eğer process_user_query hazır cevap döndürdüyse kısa devre
    if precomputed_answer:
        assistant_msg = add_message(
            db=db,
            session_id=session_id,
            sender=SenderType.assistant,
            content=precomputed_answer,
            meta_info={"reason": "precomputed_from_query_service"}
        )
        fb = feedback_crud.create_feedback(db, FeedbackCreate(
            user_id=current_user.id,
            question_id=user_msg.id,
            answer_id=assistant_msg.id,
            question_text=cleaned_query,
            answer_text=precomputed_answer,
            vote=None,
            model="rule-based"
        ))
        return {
            "answer": precomputed_answer,
            "feedback_id": str(fb.id),
            "session_id": str(session_id),
            "message_id": str(assistant_msg.id)
        }

    # 4) Retrieval (cleaned_query ile)
    topn = max(1, min(req.topn, 20))
    hits = hybrid_search(cleaned_query, topn=topn)
    passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]

    # 5) Prompt + LLM
    user_prompt = build_user_prompt(cleaned_query, passages)
    answer = query_llm(SYSTEM_PROMPT, user_prompt)

    # 6) Asistan mesajını kaydet
    assistant_msg = add_message(
        db=db,
        session_id=session_id,
        sender=SenderType.assistant,
        content=answer
    )

    # 7) Feedback kaydı
    fb = feedback_crud.create_feedback(db, FeedbackCreate(
        user_id=current_user.id,
        question_id=user_msg.id,
        answer_id=assistant_msg.id,
        question_text=cleaned_query,
        answer_text=answer,
        vote=None,
        model="qwen2.5:7b-instruct"
    ))

    return {
        "answer": answer,
        "feedback_id": str(fb.id),
        "session_id": str(session_id),
        "message_id": str(assistant_msg.id)
    }