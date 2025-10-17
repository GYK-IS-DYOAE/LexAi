from __future__ import annotations
import argparse
import re
import json
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
    MAX_PASSAGE_CHARS,
)


@dataclass
class Hit:
    doc_id: str
    score_raw: float
    score_norm: float
    source: str
    payload: Dict[str, Any]
    text_repr: str        # kısa özet
    text_full: str = ""   # LLM’e gidecek tam içerik


LAW_PAT = re.compile(
    r"\b(?:(HMK|HUMK|TBK|TMK|İK|IK|İŞ\s*KANUNU|IS\s*KANUNU|4857|6100))\s*(\d{1,3})?(?:\s*/\s*(\d{1,2}))?",
    flags=re.IGNORECASE,
)

def _device():
    return "cuda" if torch.cuda.is_available() else "cpu"

def _detect_laws(q: str) -> List[str]:
    out: List[str] = []
    for m in LAW_PAT.finditer(q or ""):
        code = (m.group(1) or "").upper().replace("IS", "İŞ").replace("IK", "İK")
        art, fik = m.group(2) or "", m.group(3) or ""
        if code in ("4857", "6100"):
            code = "İŞ KANUNU" if code == "4857" else "HMK"
        if code == "İK":
            code = "İŞ KANUNU"
        tag = code + (f" {art}" if art else "") + (f"/{fik}" if fik else "")
        if tag not in out:
            out.append(tag)
    return out

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
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60.0, prefer_grpc=True)



def _combine_full_text(payload: Dict[str, Any]) -> str:
    """
    Gerekçe, karar, hikaye, kanun atıfları gibi alanları birleştirerek
    LLM için anlamlı tam metin oluşturur.
    """
    parts: List[str] = []
    for key in ("hikaye", "gerekce", "karar", "karar_metni_meta", "text_preview"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
        elif isinstance(val, list):
            parts.extend([x.strip() for x in val if isinstance(x, str)])
    full_text = " ".join(parts).strip()
    return full_text[:MAX_PASSAGE_CHARS] if full_text else ""


def search_opensearch(query: str) -> List[Hit]:
    client = _build_opensearch()
    laws = _detect_laws(query)
    should_terms = [{"terms": {"laws_norm": laws, "boost": 3}}] if laws else []
    body = {
        "size": TOP_K_OS,
        "query": {
            "bool": {
                "must": [{
                    "multi_match": {
                        "query": query,
                        "type": "best_fields",
                        "fields": [
                            "dava_turu^4",
                            "laws_norm^3",
                            "gerekce^2",
                            "karar^1.5",
                            "hikaye^1",
                        ],
                        "operator": "and",
                    }
                }],
                "should": should_terms
            }
        }
    }

    res = client.search(index=OS_INDEX, body=body)
    hits = res.get("hits", {}).get("hits", []) or []
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
            text_repr=_first_sentence(_combine_full_text(src), 250),
            text_full=_combine_full_text(src)
        ))
    return out


def search_qdrant(query: str, model: SentenceTransformer) -> List[Hit]:
    client = _build_qdrant()
    qvec = model.encode(query.strip(), normalize_embeddings=True).tolist()
    pts = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=qvec,
        limit=TOP_K_QDRANT,
        with_payload=True,
        search_params=rest.SearchParams(quantization=rest.QuantizationSearchParams(ignore=True))
    ).points or []

    scores = [float(getattr(p, "score", 0.0) or 0.0) for p in pts]
    scores_norm = _minmax_norm(scores)

    out: List[Hit] = []
    for p, s_norm in zip(pts, scores_norm):
        payload = getattr(p, "payload", {}) or {}
        doc_id = str(payload.get("doc_id") or getattr(p, "id", "") or "")
        if not doc_id:
            continue
        out.append(Hit(
            doc_id=doc_id,
            score_raw=float(getattr(p, "score", 0.0) or 0.0),
            score_norm=s_norm,
            source="qdrant",
            payload=payload,
            text_repr=_first_sentence(_combine_full_text(payload), 250),
            text_full=_combine_full_text(payload)
        ))
    return out


def _minmax_norm(vals: List[float]) -> List[float]:
    if not vals:
        return []
    mn, mx = float(min(vals)), float(max(vals))
    if mx <= mn:
        return [1.0 for _ in vals]
    return [(x - mn) / (mx - mn) for x in vals]

def _first_sentence(t: str, max_len: int = 220) -> str:
    t = (t or "").strip()
    if not t:
        return ""
    s = re.split(r"(?<=[\.\!\?])\s+", t)[0]
    return (s[:max_len] + "…") if len(s) > max_len else s

def fuse_hits(os_hits: List[Hit], qd_hits: List[Hit], user_query: str) -> List[Hit]:
    laws = _detect_laws(user_query)
    alpha_dense, beta_bm25 = (0.6, 0.4) if laws else (0.7, 0.3)

    by_id: Dict[str, Dict[str, float]] = {}
    payload_by_id: Dict[str, Dict[str, Any]] = {}
    text_by_id: Dict[str, Tuple[str, str]] = {}  # (repr, full)

    for h in os_hits + qd_hits:
        by_id.setdefault(h.doc_id, {})[h.source] = h.score_norm
        if h.doc_id not in payload_by_id:
            payload_by_id[h.doc_id] = h.payload
            text_by_id[h.doc_id] = (h.text_repr, h.text_full)

    fused: List[Hit] = []
    for doc_id, comps in by_id.items():
        dense = comps.get("qdrant", 0.0)
        bm25 = comps.get("opensearch", 0.0)
        combined = alpha_dense * dense + beta_bm25 * bm25
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
    embs = model.encode([c.text_full for c in candidates], normalize_embeddings=True)
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
    os_hits = search_opensearch(query)
    qd_hits = search_qdrant(query, model)
    fused = fuse_hits(os_hits, qd_hits, query)
    picked = mmr_select(query, fused, model, top_n=topn, lambda_=MMR_LAMBDA)
    return picked
