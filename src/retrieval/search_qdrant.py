import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer
import torch

"""
search_qdrant.py
-------------------
Amaç:
- Kullanıcının yazdığı serbest metin sorgusunu (`query`) embedding’e çevirerek
  Qdrant içindeki vektörler arasında arama yapmak.
- En benzer kararları getirir.

Girdi:
- Komut satırından query argümanı
- Qdrant koleksiyonu: lexai_cases

Çıktı:
- En benzer 5–10 kaydın doc_id, dava_turu, sonuc, karar_no bilgileri.

Nasıl çalıştırılır:
$ python scripts/search_qdrant.py "ziynet alacağı"
"""

# ==============================
# Config
# ==============================
COLLECTION_NAME = "lexai_cases"
MODEL_NAME = "BAAI/bge-m3"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

TOP_K = 5  # kaç sonuç dönecek

# ==============================
# Load model
# ==============================
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"✅ Using device: {device}")

model = SentenceTransformer(MODEL_NAME, device=device)

# ==============================
# Connect to Qdrant
# ==============================
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# ==============================
# Query
# ==============================
def search(query: str, top_k: int = TOP_K):
    # Query embedding
    query_vec = model.encode(query, normalize_embeddings=True).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vec,
        limit=top_k,
        with_payload=True,
    )

    print(f"\n🔎 Query: {query}\n")
    for i, point in enumerate(results.points, start=1):
        payload = point.payload or {}
        print(f"{i}. (score={point.score:.4f})")
        print(f"   doc_id: {payload.get('doc_id', '—')}")
        print(f"   dava_turu: {payload.get('dava_turu', '—')}")
        print(f"   sonuc: {payload.get('sonuc', '—')}")
        print(f"   metin_karar_no: {payload.get('metin_karar_no', '—')}")
        print("")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python search_qdrant.py <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    search(query)
