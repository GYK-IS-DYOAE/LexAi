from __future__ import annotations
import argparse
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from opensearchpy import OpenSearch
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer
import torch

from src.rag.config import (
    OS_HOST, OS_PORT, OS_INDEX,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
    EMBED_MODEL_NAME,
    TOP_K_OS, TOP_K_QDRANT, MMR_LAMBDA, DEFAULT_TOPN,
    MAX_PASSAGE_CHARS
)


@dataclass
class Hit:
    doc_id: str
    score_raw: float
    score_norm: float
    source: str
    payload: Dict[str, Any]
    text_repr: str
    text_full: str


def _device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _build_opensearch() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OS_HOST, "port": OS_PORT}],
        scheme="http",
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
        timeout=60,
    )


def _build_qdrant() -> QdrantClient:
    return QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        timeout=60.0,
        prefer_grpc=True,
    )


def _minmax_norm(vals: List[float]) -> List[float]:
    if not vals:
        return []
    mn, mx = float(min(vals)), float(max(vals))
    if mx <= mn:
        return [1.0 for _ in vals]
    return [(x - mn) / (mx - mn) for x in vals]


def _text_fields(payload: Dict[str, Any]) -> Tuple[str, str]:
    """
    JSONL ve Qdrant/OpenSearch kayıtlarında karar metnini çıkarır.
    - karar_metni → tam karar metni
    - karar_preview → özet
    """
    text_full = (payload.get("karar_metni_meta") or "").strip()
    text_repr = (payload.get("karar_preview") or text_full[:400]).strip()

    if len(text_full) > MAX_PASSAGE_CHARS:
        text_full = text_full[:MAX_PASSAGE_CHARS]

    return text_repr, text_full


def search_opensearch(query: str, top_k: int = TOP_K_OS) -> List[Hit]:
    client = _build_opensearch()
    body = {
        "size": top_k,
        "query": {
            "multi_match": {
                "query": query,
                "type": "best_fields",
                "fields": [
                    "dava_turu^4",
                    "laws_norm^3",
                    "karar_metni^3",
                    "karar_preview^2",
                    "sonuc^1.5"
                ],
                "operator": "and",
            }
        },
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
        repr_text, full_text = _text_fields(src)
        out.append(Hit(
            doc_id=doc_id,
            score_raw=float(h.get("_score", 0.0)),
            score_norm=s_norm,
            source="opensearch",
            payload=src,
            text_repr=repr_text,
            text_full=full_text,
        ))
    return out


def search_qdrant(query: str, model: SentenceTransformer, top_k: int = TOP_K_QDRANT) -> List[Hit]:
    client = _build_qdrant()
    qvec = model.encode(query.strip(), normalize_embeddings=True).tolist()
    pts = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=qvec,
        limit=top_k,
        with_payload=True,
        search_params=rest.SearchParams(quantization=rest.QuantizationSearchParams(ignore=True)),
    ).points or []

    scores = [float(p.score or 0.0) for p in pts]
    scores_norm = _minmax_norm(scores)

    out: List[Hit] = []
    for p, s_norm in zip(pts, scores_norm):
        payload = p.payload or {}
        doc_id = str(payload.get("doc_id") or p.id or "")
        if not doc_id:
            continue
        repr_text, full_text = _text_fields(payload)
        out.append(Hit(
            doc_id=doc_id,
            score_raw=float(p.score or 0.0),
            score_norm=s_norm,
            source="qdrant",
            payload=payload,
            text_repr=repr_text,
            text_full=full_text,
        ))
    return out


def fuse_hits(os_hits: List[Hit], qd_hits: List[Hit]) -> List[Hit]:
    by_id: Dict[str, Dict[str, float]] = {}
    payload_by_id: Dict[str, Dict[str, Any]] = {}
    text_by_id: Dict[str, Tuple[str, str]] = {}

    for h in os_hits + qd_hits:
        by_id.setdefault(h.doc_id, {})[h.source] = h.score_norm
        if h.doc_id not in payload_by_id:
            payload_by_id[h.doc_id] = h.payload
            text_by_id[h.doc_id] = (h.text_repr, h.text_full)

    fused: List[Hit] = []
    for doc_id, comps in by_id.items():
        dense = comps.get("qdrant", 0.0)
        bm25 = comps.get("opensearch", 0.0)
        combined = 0.75 * dense + 0.25 * bm25
        repr_text, full_text = text_by_id.get(doc_id, ("", ""))
        fused.append(Hit(
            doc_id=doc_id,
            score_raw=0.0,
            score_norm=combined,
            source="hybrid",
            payload=payload_by_id.get(doc_id, {}),
            text_repr=repr_text,
            text_full=full_text
        ))
    return sorted(fused, key=lambda x: x.score_norm, reverse=True)[:100]


def mmr_select(query: str, candidates: List[Hit], model: SentenceTransformer, top_n: int, lambda_: float) -> List[Hit]:
    if not candidates:
        return []
    candidates = candidates[:50]
    q = model.encode([query], normalize_embeddings=True)
    embs = model.encode([c.text_full or c.text_repr for c in candidates], normalize_embeddings=True)
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
        print(f"   preview: {h.text_repr[:300]}...\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", type=str)
    ap.add_argument("--topn", type=int, default=DEFAULT_TOPN)
    a = ap.parse_args()

    print(f"Query: {a.query}")
    res = hybrid_search(a.query, topn=a.topn)
    print("\nHibrit sonuçlar (MMR):")
    _print(res)
