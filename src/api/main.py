# src/api/main.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
from src.retrieval.retrieve_combined import hybrid_search
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.query_llm import query_llm  # henüz yazacağız
from src.rag.validator import validate_answer_json

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    topn: int = 8

@app.post("/ask")
def ask(req: QueryRequest):

    hits = hybrid_search(req.query, topn=req.topn)
    passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]

    user_prompt = build_user_prompt(req.query, passages)

    answer = query_llm(SYSTEM_PROMPT, user_prompt)

    #validate_answer_json(answer)

    return {"answer": answer}
