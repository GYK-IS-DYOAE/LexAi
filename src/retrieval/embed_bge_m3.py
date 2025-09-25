import json
import numpy as np
from pathlib import Path
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

"""
embed_bge_m3.py
-------------------
Amaç:
- BAAI/bge-m3 modelini kullanarak karar metinlerinin embedding’ini üretmek.
- Embeddingleri `.npy` dosyasına ve metadata’yı `.jsonl` dosyasına kaydetmek.
- Aynı zamanda Qdrant veritabanına (Docker’da çalışan) batch halinde yüklemek.

Girdi:
- data/processed/records.jsonl  (flatten edilmiş karar verisi)

Çıktı:
- data/processed/embeddings.npy
- data/processed/metadata.jsonl
- Qdrant koleksiyonu: lexai_cases

Bağımlılıklar:
- Python paketleri: sentence-transformers, qdrant-client, torch, numpy, tqdm
- Donanım: Apple Silicon'da `mps` backend kullanır, GPU yoksa CPU çalışır.
- Docker: Qdrant’ın çalışıyor olması gerekir.
  👉 Qdrant başlatmak için:
     $ docker run -p 6333:6333 qdrant/qdrant

Nasıl çalıştırılır:
$ python scripts/embed_bge_m3.py
"""

# ==============================
# Config
# ==============================
INPUT_FILE = "data/processed/records.jsonl"
EMB_FILE = "data/processed/embeddings.npy"
META_FILE = "data/processed/metadata.jsonl"

COLLECTION_NAME = "lexai_cases"

# Qdrant local docker bağlantısı
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

BATCH_SIZE = 32  # Apple Silicon CPU için düşük tut
MODEL_NAME = "BAAI/bge-m3"
MAX_RECORDS = 1000  # 🔹 Test için sınır

# ==============================
# Load model
# ==============================
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"✅ Using device: {device}")

model = SentenceTransformer(MODEL_NAME, device=device)

# ==============================
# Read data
# ==============================
records, metas = [], []
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if idx >= MAX_RECORDS:  # 🔹 sadece ilk 1000 kayıt
            break
        rec = json.loads(line)

        # Her alanı ayrı ayrı embedding için ayırıyoruz
        for section in ["karar", "gerekce", "hikaye"]:
            if rec.get(section):
                if isinstance(rec[section], list):
                    texts = rec[section]
                else:
                    texts = [rec[section]]

                for t in texts:
                    records.append(t)
                    metas.append({
                        "doc_id": f"{rec['doc_id']}_{section}",
                        "section": section,
                        "dava_turu": rec.get("dava_turu"),
                        "taraf_iliskisi": rec.get("taraf_iliskisi"),
                        "sonuc": rec.get("sonuc"),
                        "metin_esas_no": rec.get("metin_esas_no"),
                        "metin_karar_no": rec.get("metin_karar_no"),
                        "kanun_atiflari": rec.get("kanun_atiflari"),
                        "onemli_tarihler": rec.get("onemli_tarihler"),
                    })

print(f"✅ Prepared {len(records)} text segments from {MAX_RECORDS} records")

# ==============================
# Embedding hesaplama
# ==============================
all_embeddings = []
for i in tqdm(range(0, len(records), BATCH_SIZE), desc="Embedding batches"):
    batch_texts = records[i:i + BATCH_SIZE]
    emb = model.encode(batch_texts, batch_size=BATCH_SIZE, normalize_embeddings=True)
    all_embeddings.append(emb)

all_embeddings = np.vstack(all_embeddings)
print(f"✅ Embedding shape: {all_embeddings.shape}")

# ==============================
# Save local files
# ==============================
Path("data/processed").mkdir(parents=True, exist_ok=True)
np.save(EMB_FILE, all_embeddings)

with open(META_FILE, "w", encoding="utf-8") as f:
    for m in metas:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")

print(f"💾 Saved embeddings -> {EMB_FILE}")
print(f"💾 Saved metadata -> {META_FILE}")

# ==============================
# Qdrant insert
# ==============================
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Collection oluştur (varsa reset)
client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=rest.VectorParams(
        size=all_embeddings.shape[1],
        distance=rest.Distance.COSINE
    )
)

print("🚀 Uploading to Qdrant...")
for i in tqdm(range(0, len(all_embeddings), 1000), desc="Qdrant upload"):
    batch_vecs = all_embeddings[i:i + 1000]
    batch_meta = metas[i:i + 1000]

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            rest.PointStruct(
                id=i + j,  # 🔹 benzersiz ID verelim
                vector=vec.tolist(),
                payload=m
            )
            for j, (m, vec) in enumerate(zip(batch_meta, batch_vecs))
        ]
    )

print("🎉 Test embeddings uploaded to Qdrant successfully!")
