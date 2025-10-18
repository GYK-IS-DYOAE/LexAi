<<<<<<< HEAD
# src/retrieval/embed_bge_m3.py
# ---------------------------------------------------------------------
# Windows friendly, STREAMING (no big temp files), single-thread
# - CUDA varsa kullanır; yoksa CPU
# - Qdrant gRPC + küçük upsert batch (128) + 'payload too large' gelirse otomatik böl
# - Her CHUNK tamamlanınca state güncellenir → yeniden açınca son TAM chunk'tan devam
# - Depolamayı azaltmak için: INT8 quantization + payload'ta tam metni tutma (preview + sha1)
# - gRPC ID gereksinimi için: point id = deterministik 64-bit int (make_point_id)
# ---------------------------------------------------------------------

=======
>>>>>>> 4c21606 (update: local llm improvements)
import json, time, hashlib
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

import numpy as np
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer, models
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest


# ======================= CONFIG =======================

# ================== Config ==================
INPUT_FILE = "data/interim/balanced_total30k.jsonl"

OUT_DIR = Path("data/processed/embeddings")
STATE_FILE = OUT_DIR / "state.json"

COLLECTION_NAME = "lexai_cases"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_GRPC_PORT = 6334

<<<<<<< HEAD
CHUNK_SIZE_RECORDS = 3_000       # her 3k kayıt = 1 chunk (CPU/RAM)
EMB_BATCH_SIZE = 32             
QDRANT_UPSERT_BATCH = 128        # 32MB limitine takılmamak için

MODEL_NAME = "BAAI/bge-m3"
=======
EMB_BATCH_SIZE = 8
QDRANT_UPSERT_BATCH = 128

USE_MODEL = "bge_m3"  # "legal", "bilkent" veya "bge_m3"
ENABLE_INT8_QUANTIZATION = True
>>>>>>> 4c21606 (update: local llm improvements)
QDRANT_REQUEST_TIMEOUT = 120.0
UPSERT_MAX_RETRIES = 5
UPSERT_BACKOFF_BASE = 2.0

<<<<<<< HEAD
# Metin parçalama
CHUNK_CHAR = 1500
CHUNK_OVERLAP = 100
MIN_CHAR = 40

# Depolama/metadata 
SAVE_TEMP_FILES = False       
STORE_FULL_TEXT_IN_QDRANT = False
TEXT_PREVIEW_CHARS = 200        
DECISION_PREVIEW_CHARS = 1000    
ENABLE_INT8_QUANTIZATION = True  
=======
DECISION_PREVIEW_CHARS = 1000
MAX_DECISION_META_CHARS = 12000
MAX_EMBED_CHARS = 2000  # sadece ilk 2000 karakter embed edilir

>>>>>>> 4c21606 (update: local llm improvements)

# ======================= HELPERS =======================

def sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

def make_point_id(m: Dict[str, Any]) -> int:
<<<<<<< HEAD
    """Deterministik 64-bit int ID."""
    base = f"{m.get('doc_id','')}|{m.get('section','')}|{m.get('text_sha1','')}"
    # SHA1'den ilk 16 hex = 64-bit integer
=======
    base = f"{m.get('doc_id','')}|{m.get('text_sha1','')}"
>>>>>>> 4c21606 (update: local llm improvements)
    return int(hashlib.sha1(base.encode("utf-8")).hexdigest()[:16], 16)

def _norm_laws(kanun_atiflari: List[Dict[str, Any]] | None) -> List[str]:
    out = []
    for k in kanun_atiflari or []:
        law = (k.get("kanun") or "").strip().upper()
        art = (k.get("madde") or "").strip()
        fik = (k.get("fikra") or "").strip()
        if law and art:
            out.append(f"{law} {art}" + (f"/{fik}" if fik else ""))
    return out

<<<<<<< HEAD
def add_text_segment(records: List[str], metas: List[Dict[str,Any]],
                     text: Any, rec: Dict[str,Any], section: str) -> None:
    """Bölüm metnini (gerekçe/hikaye) parçalara böl ve payload hazırla.
       Karar metni embed edilmez; preview'ı metadata olarak eklenir."""
    if text is None: return
    karar_full = (rec.get("karar") or rec.get("karar_metni") or "").strip()
    karar_preview = karar_full[:DECISION_PREVIEW_CHARS] if karar_full else None

    texts = text if isinstance(text, list) else [text]
    for t in texts:
        if not isinstance(t, str): continue
        t = t.strip()
        if not t: continue
        for _ci, (_start, _end, piece) in enumerate(chunk_text(t, CHUNK_CHAR, CHUNK_OVERLAP)):
            if len(piece.strip()) < MIN_CHAR: continue
            payload = {
                "doc_id": rec.get("doc_id"),
                "section": section,
                "dava_turu": rec.get("dava_turu"),
                "sonuc": rec.get("sonuc"),
                "metin_esas_no": rec.get("metin_esas_no"),
                "metin_karar_no": rec.get("metin_karar_no"),
                "kanun_atiflari": rec.get("kanun_atiflari"),
                "adimlar": [
                    {"no": i+1, "aciklama": a}
                    for i, a in enumerate(safe_list(rec.get("adimlar")))
                ],
                "text_sha1": sha1(piece),
            }
            if STORE_FULL_TEXT_IN_QDRANT:
                payload["text"] = piece
            else:
                payload["text_preview"] = piece[:TEXT_PREVIEW_CHARS]
            if karar_preview:
                payload["karar_preview"] = karar_preview

            records.append(piece)
            metas.append(payload)

def load_state() -> Dict[str,Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"next_line": 0, "chunk_idx": 0, "collection_ready": False}

def save_state(state: Dict[str,Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def ensure_collection(client: QdrantClient, vector_size: int, state: Dict[str,Any]) -> None:
    if state.get("collection_ready"):
        return
    try:
        client.get_collection(COLLECTION_NAME)
        state["collection_ready"] = True
        save_state(state)
        return
    except Exception:
        pass
    vectors_cfg = rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE)
    if ENABLE_INT8_QUANTIZATION:
        vectors_cfg.quantization_config = rest.ScalarQuantization(
            scalar=rest.ScalarQuantizationConfig(
                type=rest.ScalarType.INT8, quantile=1.0, always_ram=False
            )
        )
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=vectors_cfg,
        hnsw_config=rest.HnswConfigDiff(m=32, ef_construct=256),
    )
    state["collection_ready"] = True
    save_state(state)

def upsert_with_retry(client: QdrantClient, points: List[rest.PointStruct]) -> None:
    delay = 1.0
    cur = points
    for attempt in range(UPSERT_MAX_RETRIES):
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=cur, wait=True)
            return
        except UnexpectedResponse as e:
            if "larger than allowed" in str(e) and len(cur) > 1:
                mid = len(cur) // 2
                upsert_with_retry(client, cur[:mid])
                upsert_with_retry(client, cur[mid:])
                return
            if attempt == UPSERT_MAX_RETRIES - 1: raise
        except ResponseHandlingException:
            if attempt == UPSERT_MAX_RETRIES - 1: raise
        except Exception:
            if attempt == UPSERT_MAX_RETRIES - 1: raise
        time.sleep(delay); delay *= UPSERT_BACKOFF_BASE

def pick_device() -> str:
=======
def optimize_torch_for_env():
>>>>>>> 4c21606 (update: local llm improvements)
    if torch.cuda.is_available():
        try:
            torch.set_float32_matmul_precision("high")
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            print("GPU optimization enabled (TF32 + mixed precision).")
        except Exception:
            pass
    else:
        print("Running on CPU.")


# ======================= MODEL =======================

def load_embedding_model(device: str) -> SentenceTransformer:
    if USE_MODEL == "legal":
        print("Using model: msbayindir/legal-text-embedding-turkish-v1")
        return SentenceTransformer("msbayindir/legal-text-embedding-turkish-v1", device=device)
    elif USE_MODEL == "bilkent":
        print("Using model: KocLab-Bilkent/BERTurk-Legal")
        w = models.Transformer("KocLab-Bilkent/BERTurk-Legal", max_seq_length=512)
        p = models.Pooling(w.get_word_embedding_dimension(), True, False, False)
        return SentenceTransformer(modules=[w, p], device=device)
    elif USE_MODEL == "bge_m3":
        print("Using model: BAAI/bge-m3")
        model = SentenceTransformer("BAAI/bge-m3", device=device)
        model.max_seq_length = 512
        return model
    else:
        raise ValueError("USE_MODEL 'legal' | 'bilkent' | 'bge_m3' olmalı")

def pick_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


# ======================= EMBEDDING =======================

def add_record(records: List[str], metas: List[Dict[str, Any]], rec: Dict[str, Any]) -> None:
    karar_full = (rec.get("karar_metni") or "").strip()
    if not karar_full:
        return

    karar_preview = karar_full[:DECISION_PREVIEW_CHARS]
    karar_full_trim = karar_full[:MAX_DECISION_META_CHARS]
    karar_for_embedding = karar_full[:MAX_EMBED_CHARS]  # yalnızca ilk 2000 karakter

    payload = {
        "doc_id": rec.get("doc_id"),
        "dava_turu": rec.get("dava_turu"),
        "sonuc": rec.get("sonuc"),
        "metin_esas_no": rec.get("metin_esas_no"),
        "metin_karar_no": rec.get("metin_karar_no"),
        "kanun_atiflari": rec.get("kanun_atiflari"),
        "laws_norm": _norm_laws(rec.get("kanun_atiflari")),
        "karar_metni_meta": karar_full_trim,   # tam metin (frontend için)
        "karar_preview": karar_preview,         # kısa özet
        "text_sha1": sha1(karar_full),
    }

    records.append(karar_for_embedding)
    metas.append(payload)


@dataclass
class ChunkPack:
    idx: int
    next_line_after: int
    records: List[str]
    metas: List[Dict[str, Any]]


def upsert_with_retry(client: QdrantClient, points: List[rest.PointStruct]) -> None:
    delay = 1.0
    for attempt in range(UPSERT_MAX_RETRIES):
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
            return
        except Exception:
            if attempt == UPSERT_MAX_RETRIES - 1:
                raise
            time.sleep(delay)
            delay *= UPSERT_BACKOFF_BASE


def process_and_upload_chunk(model: SentenceTransformer, client: QdrantClient, pack: ChunkPack) -> None:
    recs, metas = pack.records, pack.metas
    if not recs:
        return

    print(f"\nEncoding chunk {pack.idx} ({len(recs)} records)...")
    all_embeddings = []
    pbar = tqdm(total=len(recs), desc=f"Chunk {pack.idx} encoding", ncols=80)

    for i in range(0, len(recs), EMB_BATCH_SIZE):
        batch = recs[i:i+EMB_BATCH_SIZE]

        if torch.cuda.is_available():
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                e = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        else:
            e = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)

        all_embeddings.append(e)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        pbar.update(len(batch))

    pbar.close()
    emb = np.vstack(all_embeddings)

    # Qdrant upload aşaması için ayrı çubuk
    for s in tqdm(range(0, len(emb), QDRANT_UPSERT_BATCH), desc=f"Chunk {pack.idx} upload", ncols=80):
        vecs = emb[s:s+QDRANT_UPSERT_BATCH]
        meta_slice = metas[s:s+QDRANT_UPSERT_BATCH]
        points = []
        for m_payload, v in zip(meta_slice, vecs):
            pid = make_point_id(m_payload)  # <- gRPC uyumlu int64 ID
            points.append(rest.PointStruct(id=pid, vector=v.tolist(), payload=m_payload))
        upsert_with_retry(client, points)


<<<<<<< HEAD
    # (Opsiyonel) upload başarılıysa geçici dosyaları sil
    if SAVE_TEMP_FILES:
        try:
            (OUT_DIR / f"embeddings_chunk_{pack.idx}.npy").unlink(missing_ok=True)
            (OUT_DIR / f"metadata_chunk_{pack.idx}.jsonl").unlink(missing_ok=True)
        except Exception:
            pass
=======
# ======================= QDRANT =======================

def ensure_collection(client: QdrantClient, vector_size: int):
    try:
        info = client.get_collection(COLLECTION_NAME)
        dim = info.config.params.vectors.size
        if dim != vector_size:
            print("Vector dimension mismatch. Deleting old collection...")
            client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    if COLLECTION_NAME not in [c.name for c in client.get_collections().collections]:
        print(f"Creating Qdrant collection '{COLLECTION_NAME}'...")
        vectors_cfg = rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE)
        if ENABLE_INT8_QUANTIZATION:
            vectors_cfg.quantization_config = rest.ScalarQuantization(
                scalar=rest.ScalarQuantizationConfig(type=rest.ScalarType.INT8, quantile=1.0, always_ram=False)
            )
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=vectors_cfg,
            hnsw_config=rest.HnswConfigDiff(m=32, ef_construct=256),
        )
        print("Collection created.")


# ======================= MAIN =======================
>>>>>>> 4c21606 (update: local llm improvements)

def main():
    p = Path(INPUT_FILE)
    if not p.exists():
        raise FileNotFoundError(f"INPUT_FILE not found: {p.resolve()}")

<<<<<<< HEAD
    # model
    model = SentenceTransformer(MODEL_NAME, device=device)
=======
    device = pick_device()
    print(f"Using device: {device}")
    optimize_torch_for_env()
    model = load_embedding_model(device)
>>>>>>> 4c21606 (update: local llm improvements)
    vector_size = model.get_sentence_embedding_dimension()

    # qdrant (gRPC)
    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        grpc_port=QDRANT_GRPC_PORT,
        prefer_grpc=True,
        timeout=QDRANT_REQUEST_TIMEOUT,
    )
<<<<<<< HEAD
    _ = client.get_collections()  # health check

    # state & collection
    state = load_state()
    ensure_collection(client, vector_size, state)
    next_line = state.get("next_line", 0)
    chunk_idx = state.get("chunk_idx", 0)
    print(f"▶ Resuming from line {next_line}, chunk {chunk_idx}")
=======
>>>>>>> 4c21606 (update: local llm improvements)

    ensure_collection(client, vector_size)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records: List[str] = []
    metas: List[Dict[str, Any]] = []
    chunk_idx = 0

    print("\n🚀 Embedding süreci başladı...\n")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(tqdm(f, desc="📖 JSONL okuma", ncols=80)):
            rec = json.loads(line)
            add_record(records, metas, rec)

<<<<<<< HEAD
                add_text_segment(records, metas, rec.get("gerekce"), rec, "gerekce")
                add_text_segment(records, metas, rec.get("hikaye"),  rec, "hikaye")

                lines_in_chunk += 1
                if lines_in_chunk == CHUNK_SIZE_RECORDS:
                    print(f"[Reader] Chunk {chunk_idx} | records_in_chunk={lines_in_chunk} | segments={len(records)}")
                    process_and_upload_chunk(
                        model, client,
                        ChunkPack(idx=chunk_idx, next_line_after=line_idx+1, records=records, metas=metas)
                    )
                    # chunk tamamlandı → state ilerlet
                    state["chunk_idx"] = chunk_idx + 1
                    state["next_line"] = line_idx + 1
                    save_state(state)

                    # sıfırla
                    chunk_idx += 1
                    records, metas = [], []
                    lines_in_chunk = 0

            # dosya sonu
            if lines_in_chunk > 0 and records:
                print(f"[Reader] Chunk {chunk_idx} (final) | records_in_chunk={lines_in_chunk} | segments={len(records)}")
                process_and_upload_chunk(
                    model, client,
                    ChunkPack(idx=chunk_idx, next_line_after=line_idx+1, records=records, metas=metas)
                )
                state["chunk_idx"] = chunk_idx + 1
                state["next_line"] = line_idx + 1
                save_state(state)

        print("🎉 Done.")
    except KeyboardInterrupt:
        print("\nInterrupted by user. (Son TAM chunk'a kadar yüklendi)")
    except Exception as e:
        print(f"Hata: {e}")
        raise
=======
            if len(records) >= 3000:
                process_and_upload_chunk(model, client, ChunkPack(idx=chunk_idx, next_line_after=line_idx+1, records=records, metas=metas))
                chunk_idx += 1
                records, metas = [], []

        if records:
            process_and_upload_chunk(model, client, ChunkPack(idx=chunk_idx, next_line_after=line_idx+1, records=records, metas=metas))

    print("\n✅ All embeddings uploaded successfully.\n")

>>>>>>> 4c21606 (update: local llm improvements)

if __name__ == "__main__":
    main()
