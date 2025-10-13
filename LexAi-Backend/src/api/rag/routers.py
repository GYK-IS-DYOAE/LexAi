from uuid import uuid4
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.auth.security import get_current_user
from src.models.auth.user_model import User
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm
from src.retrieval.retrieve_combined import hybrid_search
from src.models.feedback import feedback_crud
from src.models.feedback.feedback_schemas import FeedbackCreate
from src.core.db import SessionLocal

router = APIRouter(tags=["RAG"])


class QueryRequest(BaseModel):
    query: str
    topn: int = 8


class AskResponse(BaseModel):
    answer: str
    feedback_id: str  # Feedback ID, oy için kullanılacak


@router.post("/ask", response_model=AskResponse)
def ask(
    req: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Kullanıcının sorgusunu işler ve cevabı feedback kaydıyla birlikte döner (oy bilgisi olmadan)."""
    hits = hybrid_search(req.query, topn=req.topn)
    passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]

    print(f"[{current_user.email}] QUERY:", req.query)

    user_prompt = build_user_prompt(req.query, passages)
    answer = query_llm(SYSTEM_PROMPT, user_prompt)

    # Cevap üretildi → Şimdi oy içermeyen bir feedback kaydı oluştur
    db = SessionLocal()
    try:
        feedback_data = FeedbackCreate(
            user_id=current_user.id,
            question_id=None,
            answer_id=uuid4(),  # Şimdilik rastgele, ileride answer tablosu olursa bağlanabilir
            question_text=req.query,
            answer_text=answer,
            vote=None,  # Kullanıcı henüz oy vermedi
            model="qwen2.5:7b-instruct"
        )
        feedback = feedback_crud.create_feedback(db, feedback_data)
    finally:
        db.close()

    return {"answer": answer, "feedback_id": str(feedback.id)}
