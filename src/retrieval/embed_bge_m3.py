#LexAi/src/retrieval/embed_bge_m3.py

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
import glob

import numpy as np
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.exceptions import ResponseHandlingException

import hashlib

"""
embed_bge_m3.py
---------------
Faz-1: JSONL'den embedding dosyalarını (npy + meta jsonl) üretir. (Diskte varsa skip)
Faz-2: Diskteki embedding dosyalarını Qdrant'a yükler (uploaded_XX.ok ile skip).
Her iki faz da state.json ile kaldığı yerden devam eder.
"""

# ==============================
# Config
# ==============================
INPUT_FILE = "data/interim/balanced_total30k.jsonl"

OUT_DIR = Path("data/processed/embeddings")
STATE_FILE = OUT_DIR / "state.json"

COLLECTION_NAME = "lexai_cases"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# --- Performans ayarları ---
CHUNK_SIZE_RECORDS = 3_000       # her 3k kayıt -> 1 logical "chunk"
EMB_BATCH_SIZE = 32              # M1 Air için 16-32 arası güvenli
QDRANT_UPSERT_BATCH = 500        # sorun olursa 200'e düşür
MODEL_NAME = "BAAI/bge-m3"

QDRANT_REQUEST_TIMEOUT = 300.0   # 5 dakika
UPSERT_MAX_RETRIES = 5
UPSERT_BACKOFF_BASE = 2.0

# Chunking (metin içinde)
CHUNK_CHAR = 1500
CHUNK_OVERLAP = 100
MIN_CHAR = 40

# ==============================
# Helpers
# ==============================

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def safe_list(x: Any) -> List:
    if not x:
        return []
    return x if isinstance(x, list) else [x]

def chunk_text(txt: str, size: int = CHUNK_CHAR, overlap: int = CHUNK_OVERLAP) -> List[Tuple[int, int, str]]:
    txt = (txt or "").strip()
    n = len(txt)
    if n == 0:
        return []
    if n <= size:
        return [(0, n, txt)]
    pieces: List[Tuple[int, int, str]] = []
    step = max(1, size - overlap)
    i = 0
    while i < n:
        piece = txt[i:i+size]
        if not piece:
            break
        pieces.append((i, i+len(piece), piece))
        i += step
    return pieces

def add_text_segment(records: List[str], metas: List[Dict[str, Any]],
                     text: Any, rec: Dict[str, Any], section: str) -> None:
    if text is None:
        return
    texts = text if isinstance(text, list) else [text]
    for t in texts:
        if not isinstance(t, str):
            continue
        t = t.strip()
        if not t:
            continue
        for ci, (start, end, piece) in enumerate(chunk_text(t, CHUNK_CHAR, CHUNK_OVERLAP)):
            if len(piece.strip()) < MIN_CHAR:
                continue
            records.append(piece)
            metas.append({
                "doc_id": rec.get("doc_id"),
                "section": section,
                "chunk_index": ci,
                "char_start": start,
                "char_end": end,
                "text": piece,
                "dava_turu": rec.get("dava_turu"),
                "taraf_iliskisi": rec.get("taraf_iliskisi"),
                "sonuc": rec.get("sonuc"),
                "metin_esas_no": rec.get("metin_esas_no"),
                "metin_karar_no": rec.get("metin_karar_no"),
                "kanun_atiflari": rec.get("kanun_atiflari"),
                "onemli_tarihler": rec.get("onemli_tarihler"),
                "adimlar": [
                    {"no": i+1, "aciklama": a}
                    for i, a in enumerate(safe_list(rec.get("adimlar")))
                ],
            })

def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # embed_* Faz-1 için, upload_* Faz-2 için
    return {
        "embed_next_line": 0,
        "embed_chunk_idx": 0,
        "upload_last_ok_chunk": -1,   # uploaded_*.ok üzerinden de kontrol edilecek
        "collection_ready": False
    }

def save_state(state: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def ensure_collection_if_absent(client: QdrantClient, vector_size: int, state: Dict[str, Any]) -> None:
    if state.get("collection_ready"):
        return
    try:
        client.get_collection(COLLECTION_NAME)
        state["collection_ready"] = True
        save_state(state)
        return
    except Exception:
        pass
    # yoksa oluştur
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE),
        hnsw_config=rest.HnswConfigDiff(m=32, ef_construct=256)
    )
    state["collection_ready"] = True
    save_state(state)

def upsert_with_retry(client: QdrantClient, points: List[rest.PointStruct]) -> None:
    delay = 1.0
    for attempt in range(UPSERT_MAX_RETRIES):
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            return
        except ResponseHandlingException:
            if attempt == UPSERT_MAX_RETRIES - 1:
                raise
            time.sleep(delay)
            delay *= UPSERT_BACKOFF_BASE
        except Exception:
            if attempt == UPSERT_MAX_RETRIES - 1:
                raise
            time.sleep(delay)
            delay *= UPSERT_BACKOFF_BASE

# ==============================
# Faz-1: Embedding üretimi
# ==============================
def phase_embed_all(model: SentenceTransformer, state: Dict[str, Any]) -> None:
    next_line = state.get("embed_next_line", 0)
    chunk_idx = state.get("embed_chunk_idx", 0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"▶️ [Phase-1] Resume from line {next_line}, chunk {chunk_idx}")

    chunk_records: List[str] = []
    chunk_metas: List[Dict[str, Any]] = []
    lines_processed_this_run = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f):
            if line_idx < next_line:
                continue

            rec = json.loads(line)

            # alanlar
            add_text_segment(chunk_records, chunk_metas, rec.get("karar"), rec, "karar")
            add_text_segment(chunk_records, chunk_metas, rec.get("gerekce"), rec, "gerekce")
            add_text_segment(chunk_records, chunk_metas, rec.get("hikaye"), rec, "hikaye")

            lines_processed_this_run += 1

            if lines_processed_this_run % CHUNK_SIZE_RECORDS == 0:
                _embed_one_chunk(model, chunk_idx, line_idx + 1, chunk_records, chunk_metas, state)
                chunk_idx += 1
                chunk_records, chunk_metas = [], []

        # elde kalanlar
        if chunk_records:
            _embed_one_chunk(model, chunk_idx, line_idx + 1, chunk_records, chunk_metas, state)

    print("✅ [Phase-1] Embedding production finished.")

def _embed_one_chunk(model: SentenceTransformer,
                     chunk_idx: int,
                     next_line_after_chunk: int,
                     chunk_records: List[str],
                     chunk_metas: List[Dict[str, Any]],
                     state: Dict[str, Any]) -> None:
    emb_path = OUT_DIR / f"embeddings_chunk_{chunk_idx}.npy"
    meta_path = OUT_DIR / f"metadata_chunk_{chunk_idx}.jsonl"

    if emb_path.exists() and meta_path.exists():
        print(f"⏭️ [Embed] Chunk {chunk_idx} already exists on disk. Skipping compute.")
        # yine de state'i ilerlet
        state["embed_chunk_idx"] = chunk_idx + 1
        state["embed_next_line"] = next_line_after_chunk
        save_state(state)
        return

    print(f"🚀 [Embed] Chunk {chunk_idx} | segments={len(chunk_records)}")
    if not chunk_records:
        emb = np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
    else:
        all_embeddings = []
        for i in tqdm(range(0, len(chunk_records), EMB_BATCH_SIZE), desc=f"Chunk {chunk_idx} embedding"):
            batch_texts = chunk_records[i:i + EMB_BATCH_SIZE]
            emb = model.encode(batch_texts, batch_size=EMB_BATCH_SIZE, normalize_embeddings=True)
            all_embeddings.append(emb)
        emb = np.vstack(all_embeddings)

    np.save(emb_path, emb)
    with meta_path.open("w", encoding="utf-8") as f:
        for m in chunk_metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"✅ [Embed] Chunk {chunk_idx} done | vectors={emb.shape[0] if emb.size else 0}")

    state["embed_chunk_idx"] = chunk_idx + 1
    state["embed_next_line"] = next_line_after_chunk
    save_state(state)

# ==============================
# Faz-2: Qdrant'a upload
# ==============================
def phase_upload_all(client: QdrantClient, state: Dict[str, Any]) -> None:
    # diskten hazır chunk listesini çıkar
    paths = sorted(glob.glob(str(OUT_DIR / "embeddings_chunk_*.npy")),
                   key=lambda p: int(re.findall(r"embeddings_chunk_(\d+)\.npy", p)[0]))
    if not paths:
        print("ℹ️ [Phase-2] Yüklenecek embedding dosyası bulunamadı.")
        return

    last_ok = state.get("upload_last_ok_chunk", -1)
    print(f"▶️ [Phase-2] Resume from uploaded_last_ok={last_ok}")

    for emb_path_str in paths:
        m = re.findall(r"embeddings_chunk_(\d+)\.npy", emb_path_str)
        if not m:
            continue
        idx = int(m[0])
        emb_path = Path(emb_path_str)
        meta_path = OUT_DIR / f"metadata_chunk_{idx}.jsonl"
        ok_flag = OUT_DIR / f"uploaded_{idx}.ok"

        if ok_flag.exists():
            # zaten tamamlanmış
            # yine de state senkronize dursun
            if idx > last_ok:
                state["upload_last_ok_chunk"] = idx
                save_state(state)
            print(f"⏭️ [Upload] Chunk {idx} already marked OK. Skipping.")
            continue

        if not meta_path.exists():
            print(f"⚠️ [Upload] Chunk {idx}: metadata file yok, atlıyorum.")
            continue

        # yükle
        emb = np.load(emb_path)
        metas = [json.loads(line) for line in meta_path.read_text(encoding="utf-8").splitlines()]
        total = emb.shape[0] if emb is not None else 0
        print(f"🚚 [Upload] Chunk {idx} starting | vectors={total}")

        if total > 0:
            for s in tqdm(range(0, total, QDRANT_UPSERT_BATCH), desc=f"Chunk {idx} Qdrant upload"):
                batch_vecs = emb[s:s + QDRANT_UPSERT_BATCH]
                batch_meta = metas[s:s + QDRANT_UPSERT_BATCH]
                points: List[rest.PointStruct] = []
                for m_payload, vec in zip(batch_meta, batch_vecs):
                    pid = f"{m_payload.get('doc_id','?')}#{m_payload.get('section','?')}#{m_payload.get('char_start',0)}#{sha1(m_payload.get('text',''))[:8]}"
                    points.append(rest.PointStruct(id=pid, vector=vec.tolist(), payload=m_payload))
                upsert_with_retry(client, points)

        ok_flag.write_text("ok", encoding="utf-8")
        state["upload_last_ok_chunk"] = idx
        save_state(state)
        print(f"✅ [Upload] Chunk {idx} done")

    print("🎉 [Phase-2] All available chunks uploaded.")

# ==============================
# Main
# ==============================
def main():
    # Cihaz seçimi
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"✅ Using device: {device}")

    # Model (sadece Faz-1’de kullanılıyor)
    model = SentenceTransformer(MODEL_NAME, device=device)
    vector_size = model.get_sentence_embedding_dimension()

    # Qdrant client (Faz-2’de kullanılacak)
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=QDRANT_REQUEST_TIMEOUT)

    # State
    state = load_state()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Faz-1: Embedding üret
    phase_embed_all(model, state)

    # Qdrant koleksiyonu hazır mı?
    ensure_collection_if_absent(client, vector_size, state)

    # Faz-2: Upload
    phase_upload_all(client, state)

    print("✅ Done.")

if __name__ == "__main__":
    main()
