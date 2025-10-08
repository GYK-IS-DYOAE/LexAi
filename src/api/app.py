"""
app.py (FastAPI)
----------------
İki uç noktayı servis eder:
- GET /search?q=...&topn=8
    -> Hibrit arama sonuçları (doc_id, dava_turu, sonuc, kısa text)
- POST /answer  { "query": "..." }
    -> Retrieve -> Prompt -> Ollama/Qwen -> JSON Schema validate -> Sonuç

Çalıştırma:
    uvicorn src.api.app:app --reload --port 8000
Test:
    curl "http://localhost:8000/search?q=nafaka&topn=8"
    curl -X POST "http://localhost:8000/answer" -H "Content-Type: application/json" -d '{"query":"nafaka"}'
    
"""

from typing import List, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel

from src.retrieval.retrieve_combined import hybrid_search
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.rag.validator import validate_answer_json
from src.llm.engine_ollama import generate_json
from src.retrieval.config import DEFAULT_TOPN, MAX_PASSAGE_CHARS

app = FastAPI(title="LexAI Retrieval+LLM API")

class AnswerReq(BaseModel):
    query: str

@app.get("/search")
def search(q: str = Query(..., description="Sorgu metni"), topn: int = DEFAULT_TOPN):
    hits = hybrid_search(q, topn=topn)
    out = []
    for h in hits:
        p = h.payload or {}
        # kısa gösterim
        text = p.get("text") or ""
        if not text:
            # OS kaydı ise karar/gerekçe/hikaye topla
            parts = []
            for k in ("karar", "gerekce", "hikaye"):
                v = p.get(k)
                if isinstance(v, str): parts.append(v)
                elif isinstance(v, list): parts.extend([x for x in v if isinstance(x, str)])
            text = " ".join(parts)
        out.append({
            "doc_id": h.doc_id,
            "score": round(h.score_norm, 3),
            "source": h.source,
            "dava_turu": p.get("dava_turu"),
            "sonuc": p.get("sonuc"),
            "snippet": (text or "")[:MAX_PASSAGE_CHARS]
        })
    return {"query": q, "results": out}

@app.post("/answer")
def answer(body: AnswerReq):
    # 1) retrieve
    hits = hybrid_search(body.query, topn=DEFAULT_TOPN)

    # 2) pasajları hazırla
    passages = []
    for h in hits:
        p = h.payload or {}
        if "text" in p and isinstance(p["text"], str):
            txt = p["text"]
        else:
            parts = []
            for k in ("karar", "gerekce", "hikaye"):
                v = p.get(k)
                if isinstance(v, str): parts.append(v)
                elif isinstance(v, list): parts.extend([x for x in v if isinstance(x, str)])
            txt = " ".join(parts)
        passages.append({"doc_id": h.doc_id, "text": (txt or "")})

    # 3) prompt
    user_prompt = build_user_prompt(body.query, passages)

    # 4) LLM çağır
    try:
        raw = generate_json(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM hatası/parsing: {e}")

    # 5) validate
    try:
        validate_answer_json(raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"JSON validation hatası: {e}")

    # 6) yanıt
    return {
        "query": body.query,
        "answer": raw,
        "used_passages": [p["doc_id"] for p in passages]
    }
