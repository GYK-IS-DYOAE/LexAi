import json
import numpy as np
from pathlib import Path
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

"""
embed_bge_m3_chunked.py
-----------------------
Amaç:
- Anlamlı text alanlarını (karar, gerekce, hikaye, law_links.span) embed etmek.
- Embeddingleri `.npy` ve metadata’yı `.jsonl` dosyasına parça parça (chunk) kaydetmek.
- Qdrant veritabanına da batch halinde yüklemek.

Özellik:
- 10k kayıt = 1 chunk. Chunk tamamlanınca dosya yazılır.
- Resume özelliği: Eğer dosyalar varsa, kaldığı chunk’tan devam eder.
"""

# ==============================
# Config
# ==============================
INPUT_FILE = "data/processed/records.jsonl"
EMB_FILE = "data/processed/embeddings.npy"
META_FILE = "data/processed/metadata.jsonl"

COLLECTION_NAME = "lexai_cases"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

BATCH_SIZE = 32
CHUNK_SIZE = 10000
MODEL_NAME = "BAAI/bge-m3"

# ==============================
# Load model
# ==============================
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"✅ Using device: {device}")

model = SentenceTransformer(MODEL_NAME, device=device)

# ==============================
# Helpers
# ==============================
def add_text_segment(records, metas, text, rec, section, extra=None):
    if not text:
        return
    texts = text if isinstance(text, list) else [text]
    for t in texts:
        records.append(t)
        metas.append({
            "doc_id": rec["doc_id"],
            "section": section,
            "text": t,
            "dava_turu": rec.get("dava_turu"),
            "taraf_iliskisi": rec.get("taraf_iliskisi"),
            "sonuc": rec.get("sonuc"),
            "metin_esas_no": rec.get("metin_esas_no"),
            "metin_karar_no": rec.get("metin_karar_no"),
            "kanun_atiflari": rec.get("kanun_atiflari"),
            "onemli_tarihler": rec.get("onemli_tarihler"),
            "adimlar": rec.get("adimlar"),
            "law_links": rec.get("law_links"),
            "extra": extra
        })

def process_chunk(chunk_idx, chunk_records, chunk_metas, client):
    print(f"🚀 Processing chunk {chunk_idx} with {len(chunk_records)} texts")

    # Embedding
    all_embeddings = []
    for i in tqdm(range(0, len(chunk_records), BATCH_SIZE), desc=f"Chunk {chunk_idx} embedding"):
        batch_texts = chunk_records[i:i + BATCH_SIZE]
        emb = model.encode(batch_texts, batch_size=BATCH_SIZE, normalize_embeddings=True)
        all_embeddings.append(emb)
    all_embeddings = np.vstack(all_embeddings)

    # Save embeddings incrementally
    emb_path = Path(EMB_FILE)
    if emb_path.exists():
        prev = np.load(emb_path)
        combined = np.vstack([prev, all_embeddings])
        np.save(emb_path, combined)
    else:
        np.save(emb_path, all_embeddings)

    # Save metadata incrementally
    with open(META_FILE, "a", encoding="utf-8") as f:
        for m in chunk_metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    # Upload to Qdrant
    for i in tqdm(range(0, len(all_embeddings), 1000), desc=f"Chunk {chunk_idx} Qdrant upload"):
        batch_vecs = all_embeddings[i:i + 1000]
        batch_meta = chunk_metas[i:i + 1000]

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                rest.PointStruct(
                    id=(chunk_idx * CHUNK_SIZE) + i + j,
                    vector=vec.tolist(),
                    payload=m
                )
                for j, (m, vec) in enumerate(zip(batch_meta, batch_vecs))
            ]
        )

# ==============================
# Main
# ==============================
def main():
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Koleksiyonu sıfırla sadece ilk run’da
    if not Path(EMB_FILE).exists():
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=rest.VectorParams(
                size=1024,  # bge-m3 dim
                distance=rest.Distance.COSINE
            )
        )

    chunk_records, chunk_metas = [], []
    chunk_idx = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, start=1):
            rec = json.loads(line)

            add_text_segment(chunk_records, chunk_metas, rec.get("karar"), rec, "karar")
            add_text_segment(chunk_records, chunk_metas, rec.get("gerekce"), rec, "gerekce")
            add_text_segment(chunk_records, chunk_metas, rec.get("hikaye"), rec, "hikaye")
            for ll in rec.get("law_links", []) or []:
                add_text_segment(chunk_records, chunk_metas, ll.get("span"), rec, "law_links", extra=ll)

            # Chunk dolduysa işle
            if line_idx % CHUNK_SIZE == 0:
                process_chunk(chunk_idx, chunk_records, chunk_metas, client)
                chunk_idx += 1
                chunk_records, chunk_metas = [], []

        # Son kalan chunk
        if chunk_records:
            process_chunk(chunk_idx, chunk_records, chunk_metas, client)

    print("🎉 All embeddings processed and uploaded")

if __name__ == "__main__":
    main()
