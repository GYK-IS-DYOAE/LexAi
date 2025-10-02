src/retrieval/embed_bge_m3_chunked.py

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import numpy as np
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.exceptions import ResponseHandlingException

import hashlib
import threading
from queue import Queue, Empty

"""
embed_bge_m3_chunked.py
-----------------------
Amaç:
- Anlamlı text alanlarını (karar, gerekce, hikaye) embed etmek.
- Metinleri ~1500 karakterlik parçalara ayırmak (overlap ~100 char).
- Her 3.000 kayıt = 1 chunk; embedding + metadata dosyaya yazılır.
- Qdrant'a 1000'lik batchlerle yüklenir, retry/backoff ile güvenli gönderilir.
- Resume: state.json üzerinden kaldığı yerden devam eder.
- Producer-Consumer modeli ile PARALLEL embedding + upload yapılır.
"""

# ==============================
# Config
# ==============================
INPUT_FILE = "data/interim/03_validated.linked.jsonl"

OUT_DIR = Path("data/processed/embeddings")
STATE_FILE = OUT_DIR / "state.json"

COLLECTION_NAME = "lexai_cases"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# ---- Performans ayarları (istediğin değerler) ----
CHUNK_SIZE_RECORDS = 3_000     # her 3k kayıt 1 chunk
EMB_BATCH_SIZE = 32
QDRANT_UPSERT_BATCH = 1_000
MODEL_NAME = "BAAI/bge-m3"

QDRANT_REQUEST_TIMEOUT = 60.0
UPSERT_MAX_RETRIES = 5
UPSERT_BACKOFF_BASE = 2.0

CHUNK_CHAR = 1500
CHUNK_OVERLAP = 100
MIN_CHAR = 40

# Queue kapasitesi: bellek kontrolü için sınırlı
CHUNK_QUEUE_MAXSIZE = 4      # aynı anda bellekte en fazla 4 chunk beklesin
UPLOAD_QUEUE_MAXSIZE = 6     # upload bekleyen embedding batch sayısı

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
    """Metni sabit uzunlukta parçalara ayırır."""
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

SEEN_HASHES_THIS_RUN: set[str] = set()
SEEN_LOCK = threading.Lock()
def reset_seen_hashes():
    with SEEN_LOCK:
        SEEN_HASHES_THIS_RUN.clear()

def add_text_segment(records: List[str], metas: List[Dict[str, Any]],
                     text: Any, rec: Dict[str, Any], section: str,
                     extra: Optional[Dict[str, Any]] = None) -> None:
    """Bir alanı parçalara böl, çok kısa/tekrarları at, payload hazırla."""
    if text is None:
        return
    texts = text if isinstance(text, list) else [text]

    for t in texts:
        if not isinstance(t, str):
            continue
        t = t.strip()
        if not t:
            continue

        pieces = chunk_text(t, CHUNK_CHAR, CHUNK_OVERLAP)
        for ci, (start, end, piece) in enumerate(pieces):
            if len(piece.strip()) < MIN_CHAR:
                continue
            key = sha1(f"{rec.get('doc_id','?')}|{section}|{start}|{piece[:96]}")
            with SEEN_LOCK:
                if key in SEEN_HASHES_THIS_RUN:
                    continue
                SEEN_HASHES_THIS_RUN.add(key)

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
                # adımlar artık sadece sıra numarası + açıklama
                "adimlar": [
                    {"no": i+1, "aciklama": a}
                    for i, a in enumerate(safe_list(rec.get("adimlar")))
                ],
                # law_links EMBEDDING'E GİRMEZ; istersek metadata olarak burada bırakabiliriz
                # "law_links": rec.get("law_links")
            })

def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"next_line": 0, "chunk_idx": 0, "collection_ready": False}

def save_state(state: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def ensure_collection(client: QdrantClient, vector_size: int, state: Dict[str, Any]) -> None:
    if state.get("collection_ready"):
        return
    try:
        _ = client.get_collection(COLLECTION_NAME)
        state["collection_ready"] = True
        save_state(state)
        return
    except Exception:
        pass
    client.recreate_collection(
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
# Parallel Pipeline Structures
# ==============================

@dataclass
class RawChunk:
    chunk_idx: int
    next_line_after_chunk: int  # bu chunk bittikten sonra bir sonraki okuyacağımız satır
    records: List[str]
    metas: List[Dict[str, Any]]

@dataclass
class EmbeddedChunk:
    chunk_idx: int
    next_line_after_chunk: int
    embeddings: np.ndarray
    metas: List[Dict[str, Any]]
    emb_path: Path
    meta_path: Path

SENTINEL = object()

# ==============================
# Workers
# ==============================

def embed_worker(model: SentenceTransformer,
                 chunk_queue: Queue,
                 upload_queue: Queue):
    """RawChunk alır, embed eder, dosyaları yazar ve upload_queue'e koyar."""
    while True:
        item = chunk_queue.get()
        if item is SENTINEL:
            upload_queue.put(SENTINEL)
            break
        chunk: RawChunk = item
        recs = chunk.records
        metas = chunk.metas

        print(f"🚀 [Embed] Chunk {chunk.chunk_idx} starting | {len(recs)} text segments")

        if not recs:
            # Boş chunk da olsa akışı bozmamak için boş embedded chunk gönder
            emb = np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
        else:
            all_embeddings = []
            for i in tqdm(range(0, len(recs), EMB_BATCH_SIZE), desc=f"Chunk {chunk.chunk_idx} embedding"):
                batch_texts = recs[i:i + EMB_BATCH_SIZE]
                emb = model.encode(batch_texts, batch_size=EMB_BATCH_SIZE, normalize_embeddings=True)
                all_embeddings.append(emb)
            emb = np.vstack(all_embeddings)

        emb_path = OUT_DIR / f"embeddings_chunk_{chunk.chunk_idx}.npy"
        meta_path = OUT_DIR / f"metadata_chunk_{chunk.chunk_idx}.jsonl"
        np.save(emb_path, emb)

        with meta_path.open("w", encoding="utf-8") as f:
            for m in metas:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

        print(f"✅ [Embed] Chunk {chunk.chunk_idx} done | vectors: {0 if len(recs)==0 else emb.shape[0]}")
        upload_queue.put(EmbeddedChunk(
            chunk_idx=chunk.chunk_idx,
            next_line_after_chunk=chunk.next_line_after_chunk,
            embeddings=emb,
            metas=metas,
            emb_path=emb_path,
            meta_path=meta_path
        ))
        chunk_queue.task_done()

def upload_worker(client: QdrantClient,
                  state: Dict[str, Any],
                  upload_queue: Queue,
                  state_lock: threading.Lock):
    """EmbeddedChunk alır, Qdrant'a yükler, state.json'ı güvenle günceller."""
    while True:
        item = upload_queue.get()
        if item is SENTINEL:
            break
        ch: EmbeddedChunk = item

        total = ch.embeddings.shape[0] if ch.embeddings is not None else 0
        print(f"🚚 [Upload] Chunk {ch.chunk_idx} starting | vectors: {total}")

        if total > 0:
            for s in tqdm(range(0, total, QDRANT_UPSERT_BATCH), desc=f"Chunk {ch.chunk_idx} Qdrant upload"):
                batch_vecs = ch.embeddings[s:s + QDRANT_UPSERT_BATCH]
                batch_meta = ch.metas[s:s + QDRANT_UPSERT_BATCH]
                points: List[rest.PointStruct] = []
                for m, vec in zip(batch_meta, batch_vecs):
                    pid = f"{m.get('doc_id','?')}#{m.get('section','?')}#{m.get('char_start',0)}#{sha1(m.get('text',''))[:8]}"
                    points.append(rest.PointStruct(id=pid, vector=vec.tolist(), payload=m))
                upsert_with_retry(client, points)

        print(f"✅ [Upload] Chunk {ch.chunk_idx} done")

        # State güncelle (bu chunk başarıyla yüklendi)
        with state_lock:
            state["chunk_idx"] = ch.chunk_idx + 1
            state["next_line"] = ch.next_line_after_chunk
            save_state(state)

        upload_queue.task_done()

# ==============================
# Main
# ==============================

def main():
    # Cihaz seçimi (istenen: mps)
    device = "mps"
    if not torch.backends.mps.is_available():
        print("⚠️  MPS (Apple Silicon) uygun değil, CPU'ya düşüyorum.")
        device = "cpu"
    print(f"✅ Using device: {device}")

    # Model ve Qdrant
    model = SentenceTransformer(MODEL_NAME, device=device)
    vector_size = model.get_sentence_embedding_dimension()
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=QDRANT_REQUEST_TIMEOUT)

    # State & collection
    state = load_state()
    ensure_collection(client, vector_size, state)
    next_line = state.get("next_line", 0)
    chunk_idx = state.get("chunk_idx", 0)
    print(f"▶️ Resuming from line {next_line}, chunk {chunk_idx}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Kuyruklar ve kilitler
    chunk_queue: Queue = Queue(maxsize=CHUNK_QUEUE_MAXSIZE)
    upload_queue: Queue = Queue(maxsize=UPLOAD_QUEUE_MAXSIZE)
    state_lock = threading.Lock()

    # Worker thread'leri
    t_embed = threading.Thread(target=embed_worker, args=(model, chunk_queue, upload_queue), daemon=True)
    t_upload = threading.Thread(target=upload_worker, args=(client, state, upload_queue, state_lock), daemon=True)
    t_embed.start()
    t_upload.start()

    # Reader / Producer
    reset_seen_hashes()
    chunk_records: List[str] = []
    chunk_metas: List[Dict[str, Any]] = []
    lines_processed_this_run = 0

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                if line_idx < next_line:
                    continue

                rec = json.loads(line)

                # Embedding alanları: karar + gerekce + hikaye
                add_text_segment(chunk_records, chunk_metas, rec.get("karar"), rec, "karar")
                add_text_segment(chunk_records, chunk_metas, rec.get("gerekce"), rec, "gerekce")
                add_text_segment(chunk_records, chunk_metas, rec.get("hikaye"), rec, "hikaye")

                lines_processed_this_run += 1

                # Chunk dolduysa kuyrukla embedder'a gönder
                if lines_processed_this_run % CHUNK_SIZE_RECORDS == 0:
                    print(f"📦 [Reader] Enqueue chunk {chunk_idx} | records_in_chunk={CHUNK_SIZE_RECORDS} | segments={len(chunk_records)}")
                    # RawChunk paketini sıraya koy
                    chunk_queue.put(RawChunk(
                        chunk_idx=chunk_idx,
                        next_line_after_chunk=line_idx + 1,
                        records=chunk_records,
                        metas=chunk_metas
                    ))
                    # Sonraki chunk için hazırlan
                    chunk_idx += 1
                    chunk_records = []
                    chunk_metas = []
                    reset_seen_hashes()

            # Dosya bitti, elde kalanları gönder
            if chunk_records:
                print(f"📦 [Reader] Enqueue chunk {chunk_idx} (final) | records_in_chunk={(lines_processed_this_run % CHUNK_SIZE_RECORDS) or CHUNK_SIZE_RECORDS} | segments={len(chunk_records)}")
                chunk_queue.put(RawChunk(
                    chunk_idx=chunk_idx,
                    next_line_after_chunk=line_idx + 1,   # son satırdan sonrası
                    records=chunk_records,
                    metas=chunk_metas
                ))
                chunk_idx += 1
                chunk_records = []
                chunk_metas = []

        # Embedder'a bitiş sinyali
        chunk_queue.put(SENTINEL)

        # Kuyrukları boşaltmasını bekle
        chunk_queue.join()
        upload_queue.join()

    except KeyboardInterrupt:
        print("⛔ Interrupted by user, shutting down gracefully...")
    finally:
        print("🎉 All chunks processed & uploaded (or up to last successful state).")

if __name__ == "__main__":
    main()
