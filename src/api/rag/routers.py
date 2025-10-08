from fastapi import APIRouter
from pydantic import BaseModel
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm
from src.retrieval.retrieve_combined import hybrid_search

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    topn: int = 8

@router.post("/ask")
def ask(req: QueryRequest):
    hits = hybrid_search(req.query, topn=req.topn)
    passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]

    print("QUERY:", req)
    print("RETRIEVED PASSAGES:")
    for doc in passages:
        print("-", doc["text"])

    user_prompt = build_user_prompt(req.query, passages)
    answer = query_llm(SYSTEM_PROMPT, user_prompt)

    return {"answer": answer}
