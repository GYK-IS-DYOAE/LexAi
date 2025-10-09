from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.auth.security import get_current_user
from src.models.auth.user_model import User
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm
from src.retrieval.retrieve_combined import hybrid_search
from src.models.feedback import feedback_crud, feedback_schemas
from src.core.db import SessionLocal

router = APIRouter(tags=["RAG"])

class QueryRequest(BaseModel):
    query: str
    topn: int = 8

class AskResponse(BaseModel):
    answer: str
    feedback_id: str  # 👈 frontend, bu ID'yi geri bildirim butonları için kullanacak


@router.post("/ask", response_model=AskResponse)
def ask(
    req: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Kullanıcının sorgusunu işler ve cevabı feedback kaydıyla birlikte döner."""
    hits = hybrid_search(req.query, topn=req.topn)
    passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]

    print(f"[{current_user.email}] QUERY:", req.query)

    user_prompt = build_user_prompt(req.query, passages)
    answer = query_llm(SYSTEM_PROMPT, user_prompt)

    # 🔽 Cevabı otomatik feedback tablosuna kaydediyoruz
    db = SessionLocal()
    data = feedback_schemas.VoteRequest(
        query=req.query,
        response=answer,
        vote=None,
        action=None,
        notes=None
    )
    feedback = feedback_crud.create_feedback(db, user_id=current_user.id, data=data)

    return {"answer": answer, "feedback_id": str(feedback.id)}
