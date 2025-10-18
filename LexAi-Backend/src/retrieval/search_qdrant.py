import re
import sys
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer
import torch

COLLECTION_NAME = "lexai_cases"
MODEL_NAME = "BAAI/bge-m3"

QDRANT_HOST = "localhost"
HTTP_PORT = 6333
GRPC_PORT = 6334

TOP_K_DECISION = 16
TOP_K_SIGNAL = 8

KW = [
    "kira", "kira sözleşmesi", "kiracı", "kiralayan", "kiraya veren",
    "tahliye", "kira tespiti", "kira uyarlama", "tahliye taahhüdü",
    "TBK 299", "TBK 344", "TBK 350", "TBK 352"
]

def pick_device() -> str:
    if torch.cuda.is_available():
        try:
            torch.set_float32_matmul_precision("high")
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        except Exception:
            pass
        print(f"Using device: cuda | GPU: {torch.cuda.get_device_name(0)}")
        return "cuda"
    print("Using device: cpu")
    return "cpu"

def build_query_text(user_query: str) -> str:
    return user_query.strip()

device = pick_device()
model = SentenceTransformer(MODEL_NAME, device=device)

client = QdrantClient(
    host=QDRANT_HOST,
    port=HTTP_PORT,
    grpc_port=GRPC_PORT,
    prefer_grpc=True,
    timeout=60.0,
)

def sanity_checks():
    info = client.get_collection(COLLECTION_NAME)
    try:
        dim = info.config.params.vectors.size
    except Exception:
        dim = None
    try:
        model_dim = model.get_sentence_embedding_dimension()
    except Exception:
        model_dim = None
    print(f"[CHECK] collection='{COLLECTION_NAME}', vector_dim={dim}, model_dim={model_dim}")
    cnt = client.count(COLLECTION_NAME, exact=True).count
    print(f"[CHECK] points_in_collection={cnt}")

def _query_generic(c: QdrantClient, qvec, top_k: int, section_value: str):
    flt = rest.Filter(must=[rest.FieldCondition(key="section", match=rest.MatchValue(value=section_value))])
    params = rest.SearchParams(quantization=rest.QuantizationSearchParams(ignore=True))
    try:
        r = c.query_points(
            collection_name=COLLECTION_NAME,
            query=qvec,
            limit=top_k,
            with_payload=True,
            filter=flt,
            search_params=params,
        )
        return list(getattr(r, "points", []) or [])
    except AssertionError:
        r = c.search(
            collection_name=COLLECTION_NAME,
            query_vector=qvec,
            limit=top_k,
            with_payload=True,
            query_filter=flt,
            search_params=params,
        )
        return list(r or [])

def _kw_score(payload) -> int:
    text = " ".join([
        str(payload.get("text_preview") or "")[:2000],
        str(payload.get("karar_preview") or "")[:2000],
        " ".join(payload.get("laws_norm") or []),
        str(payload.get("dava_turu") or ""),
        str(payload.get("sonuc") or "")
    ]).lower()
    score = 0
    for k in KW:
        if k.lower() in text:
            score += 1
    return score

def search(user_query: str, top_k_total: int = 12):
    sanity_checks()

    qtext = build_query_text(user_query)
    qvec = model.encode(qtext, normalize_embeddings=True).tolist()
    print(f"\nQuery:\n{qtext}\n")

    c = client
    try:
        pts = _query_generic(c, qvec, TOP_K_DECISION, "decision_full")
    except Exception as e:
        print(f"gRPC failed, switching to HTTP. Reason: {e}")
        c = QdrantClient(host=QDRANT_HOST, port=HTTP_PORT, prefer_grpc=False, timeout=60.0)
        pts = _query_generic(c, qvec, TOP_K_DECISION, "decision_full")

    try:
        pts += _query_generic(c, qvec, TOP_K_SIGNAL, "signal")
    except Exception:
        pass

    if not pts:
        print("No result.")
        return

    rescored = []
    for p in pts:
        pl = getattr(p, "payload", {}) or {}
        base = float(getattr(p, "score", 0.0) or 0.0)
        kw = _kw_score(pl)
        rescored.append((0.65*base + 0.35*(kw/len(KW)), kw, p))

    rescored.sort(key=lambda t: (t[0], t[1], getattr(t[2], "score", 0.0)), reverse=True)
    final = [t[2] for t in rescored][:top_k_total]

    for i, p in enumerate(final, 1):
        pl = getattr(p, "payload", {}) or {}
        preview = pl.get("text_preview") or pl.get("karar_preview") or ""
        if isinstance(preview, list):
            preview = " ".join(preview)
        preview = (preview or "").strip().replace("\n", " ")
        if len(preview) > 180:
            preview = preview[:180] + "..."
        print(f"{i}. score={getattr(p, 'score', 0.0):.4f}")
        print(f"   doc_id:    {pl.get('doc_id', '-')}")
        print(f"   section:   {pl.get('section', '-')}")
        print(f"   dava_turu: {pl.get('dava_turu', '-')}")
        print(f"   sonuc:     {pl.get('sonuc', '-')}")
        print(f"   laws_norm: {pl.get('laws_norm', '-')}")
        print(f"   preview:   {preview}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python -m src.retrieval.search_qdrant '<sorgu>'")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    search(query)

#python src\retrieval\search_qdrant.py "kira sözleşmesi" 