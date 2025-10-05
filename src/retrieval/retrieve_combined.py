# retrieve_combined.py
# ------------------------------------------------------------
# Hibrit Retrieve:
#  - OpenSearch (BM25) ve Qdrant (semantic) ayrı ayrı top-50,
#  - skorları normalize edip doc_id bazında birleştir,
#  - MMR ile hem alaka hem çeşitlilik optimize edilerek top-N döndür.
#
# CLI:
#   python src/retrieval/retrieve_combined.py "nafaka" --topn 8
# ------------------------------------------------------------

from __future__ import annotations
import argparse
from dataclasses import dataclass
from typing import List, Dict, Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from opensearchpy import OpenSearch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import torch

from src.config import (
    OS_HOST, OS_PORT, OS_USER, OS_PASS, OS_INDEX,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
    EMBED_MODEL_NAME,
    TOP_K_OS, TOP_K_QDRANT, MMR_LAMBDA, DEFAULT_TOPN
)

@dataclass
class Hit:
    doc_id: str
    score_raw: float
    score_norm: float
    source: str               # "opensearch" | "qdrant" | "both"
    payload: Dict[str, Any]   # OS: _source, Qdrant: payload
    text_repr: str            # MMR için kısa text temsili

def _device():
    return "mps" if torch.backends.mps.is_available() else "cpu"

def _build_opensearch() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OS_HOST, "port": OS_PORT}],
        http_auth=(OS_USER, OS_PASS),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
    )

def _build_qdrant() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60.0)

def _text_repr_from_payload(payload: Dict[str, Any]) -> str:
    # Qdrant segment (payload['text'])
    t = payload.get("text")
    if isinstance(t, str) and t.strip():
        return t[:800]
    # OpenSearch tam belge alanları
    parts = []
    for k in ("karar", "gerekce", "hikaye"):
        v = payload.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend([x for x in v if isinstance(x, str)])
    if parts:
        return " ".join(parts)[:800]
    # fallback
    return str(payload.get("dava_turu") or "")[:200]

def _minmax_norm(vals: List[float]) -> List[float]:
    if not vals:
        return []
    mn, mx = float(min(vals)), float(max(vals))
    if mx <= mn:
        return [1.0 for _ in vals]
    return [(x - mn) / (mx - mn) for x in vals]

def search_opensearch(query: str, top_k: int = TOP_K_OS) -> List[Hit]:
    client = _build_opensearch()
    body = {
        "size": top_k,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["dava_turu", "taraf_iliskisi", "sonuc", "karar", "gerekce", "hikaye"],
            }
        }
    }
    res = client.search(index=OS_INDEX, body=body)
    hits = res.get("hits", {}).get("hits", [])
    scores = [float(h.get("_score", 0.0)) for h in hits]
    scores_norm = _minmax_norm(scores)

    out: List[Hit] = []
    for h, s_norm in zip(hits, scores_norm):
        src = h.get("_source", {}) or {}
        doc_id = str(src.get("doc_id") or h.get("_id") or "")
        if not doc_id:
            continue
        out.append(Hit(
            doc_id=doc_id,
            score_raw=float(h.get("_score", 0.0)),
            score_norm=s_norm,
            source="opensearch",
            payload=src,
            text_repr=_text_repr_from_payload(src),
        ))
    return out

def search_qdrant(query: str, model: SentenceTransformer, top_k: int = TOP_K_QDRANT) -> List[Hit]:
    client = _build_qdrant()
    qvec = model.encode(query, normalize_embeddings=True).tolist()
    res = client.query_points(QDRANT_COLLECTION, qvec, limit=top_k, with_payload=True)
    pts = getattr(res, "points", []) or []
    scores = [float(p.score or 0.0) for p in pts]
    scores_norm = _minmax_norm(scores)

    out: List[Hit] = []
    for p, s_norm in zip(pts, scores_norm):
        payload = p.payload or {}
        doc_id = str(payload.get("doc_id") or p.id or "")
        if not doc_id:
            continue
        out.append(Hit(
            doc_id=doc_id,
            score_raw=float(p.score or 0.0),
            score_norm=s_norm,
            source="qdrant",
            payload=payload,
            text_repr=_text_repr_from_payload(payload),
        ))
    return out

def fuse_hits(os_hits: List[Hit], qd_hits: List[Hit]) -> List[Hit]:
    fused = {h.doc_id: h for h in os_hits}
    for h in qd_hits:
        if h.doc_id in fused:
            a = fused[h.doc_id]
            fused_score = (a.score_norm + h.score_norm) / 2.0
            payload = a.payload if a.source == "opensearch" else h.payload
            text_repr = a.text_repr or h.text_repr
            fused[h.doc_id] = Hit(
                doc_id=h.doc_id,
                score_raw=0.0,
                score_norm=fused_score,
                source="both",
                payload=payload,
                text_repr=text_repr,
            )
        else:
            fused[h.doc_id] = h
    # ilk 100
    return sorted(fused.values(), key=lambda x: x.score_norm, reverse=True)[:100]

def mmr_select(query: str, candidates: List[Hit], model: SentenceTransformer, top_n: int, lambda_: float) -> List[Hit]:
    if not candidates:
        return []
    candidates = candidates[:50]
    q = model.encode([query], normalize_embeddings=True)
    embs = model.encode([c.text_repr for c in candidates], normalize_embeddings=True)
    rel = cosine_similarity(embs, q).reshape(-1)

    selected = []
    remaining = list(range(len(candidates)))
    first = int(np.argmax(rel))
    selected.append(first)
    remaining.remove(first)

    while len(selected) < min(top_n, len(candidates)) and remaining:
        max_score, best = -1e9, None
        for j in remaining:
            div = cosine_similarity(embs[j:j+1], embs[selected]).max()
            mmr = lambda_ * rel[j] - (1 - lambda_) * div
            if mmr > max_score:
                max_score, best = mmr, j
        selected.append(best)
        remaining.remove(best)
    return [candidates[i] for i in selected]

def hybrid_search(query: str, topn: int = DEFAULT_TOPN) -> List[Hit]:
    model = SentenceTransformer(EMBED_MODEL_NAME, device=_device())
    os_hits = search_opensearch(query, TOP_K_OS)
    qd_hits = search_qdrant(query, model, TOP_K_QDRANT)
    fused = fuse_hits(os_hits, qd_hits)
    picked = mmr_select(query, fused, model, top_n=topn, lambda_=MMR_LAMBDA)
    return picked

def _print(hits: List[Hit]):
    for i, h in enumerate(hits, 1):
        p = h.payload or {}
        print(f"{i}. score={h.score_norm:.3f} | src={h.source} | doc_id={h.doc_id} | "
              f"dava_turu={p.get('dava_turu','—')} | sonuc={p.get('sonuc','—')}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", type=str)
    ap.add_argument("--topn", type=int, default=DEFAULT_TOPN)
    a = ap.parse_args()

    print(f"🔎 Query: {a.query}")
    res = hybrid_search(a.query, topn=a.topn)
    print("\n📌 Hibrit sonuçlar (MMR)")
    _print(res)
