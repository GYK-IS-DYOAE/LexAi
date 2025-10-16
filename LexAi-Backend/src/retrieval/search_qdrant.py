# src/retrieval/search_qdrant.py
import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer
import torch

COLLECTION_NAME = "lexai_cases"
MODEL_NAME = "BAAI/bge-m3"

QDRANT_HOST = "localhost"
HTTP_PORT = 6333
GRPC_PORT = 6334

TOP_K = 8

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
    dim = info.vectors_count or info.config.params.vectors.size  # versiyona göre farklı alanlar olabilir
    try:
        model_dim = model.get_sentence_embedding_dimension()
    except Exception:
        model_dim = None
    print(f"[CHECK] collection='{COLLECTION_NAME}', vector_dim={dim}, model_dim={model_dim}")
    cnt = client.count(COLLECTION_NAME, exact=True).count
    print(f"[CHECK] points_in_collection={cnt}")

def query_once(qvec, top_k):
    
    search_params = rest.SearchParams(
        quantization=rest.QuantizationSearchParams(ignore=True)
    )
    return client.query_points(
        collection_name=COLLECTION_NAME,
        query=qvec,
        limit=top_k,
        with_payload=True,
        search_params=search_params,
    )

def search(query: str, top_k: int = TOP_K):
    sanity_checks()

    qvec = model.encode(query, normalize_embeddings=True).tolist()
    print(f"\nQuery: {query}\n")

    try:
        results = query_once(qvec, top_k)
    except Exception as e:
        print(f"gRPC query failed → falling back to HTTP. Reason: {e}")
        http_client = QdrantClient(host=QDRANT_HOST, port=HTTP_PORT, prefer_grpc=False, timeout=60.0)
        global client
        client = http_client
        results = query_once(qvec, top_k)

    if not results.points:
        print("⚠️ Sonuç bulunamadı.")
        return

    for i, p in enumerate(results.points, start=1):
        pl = p.payload or {}
        preview = pl.get("text_preview") or pl.get("karar_preview") or ""
        if isinstance(preview, list):
            preview = " ".join(preview)
        preview = (preview or "").strip().replace("\n", " ")
        if len(preview) > 180:
            preview = preview[:180] + "…"

        print(f"{i}. score={p.score:.4f}")
        print(f"   doc_id:   {pl.get('doc_id', '—')}")
        print(f"   section:  {pl.get('section', '—')}")
        print(f"   dava_turu:{pl.get('dava_turu', '—')}")
        print(f"   sonuc:    {pl.get('sonuc', '—')}")
        print(f"   esas_no:  {pl.get('metin_esas_no', '—')}")
        print(f"   karar_no: {pl.get('metin_karar_no', '—')}")
        print(f"   preview:  {preview}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python src\\retrieval\\search_qdrant.py <sorgu metni>")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    search(query)


#python src\retrieval\search_qdrant.py "kira sözleşmesi" 