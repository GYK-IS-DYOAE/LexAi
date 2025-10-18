# src/retrieval/embed_bge_m3.py
# ---------------------------------------------------------------------
# Windows friendly, STREAMING (no big temp files), single-thread
# - CUDA varsa kullanır; yoksa CPU
# - Qdrant gRPC + küçük upsert batch (128) + 'payload too large' gelirse otomatik böl
# - Her CHUNK tamamlanınca state güncellenir → yeniden açınca son TAM chunk'tan devam
# - Depolamayı azaltmak için: INT8 quantization + payload'ta tam metni tutma (preview + sha1)
# - gRPC ID gereksinimi için: point id = deterministik 64-bit int (make_point_id)
# ---------------------------------------------------------------------

import json, time, hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

import numpy as np
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

# ================== Config ==================
INPUT_FILE = "data/interim/balanced_total30k.jsonl"

OUT_DIR = Path("data/processed/embeddings")
STATE_FILE = OUT_DIR / "state.json"

COLLECTION_NAME = "lexai_cases"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_GRPC_PORT = 6334

CHUNK_SIZE_RECORDS = 3_000       # her 3k kayıt = 1 chunk (CPU/RAM)
EMB_BATCH_SIZE = 32             
QDRANT_UPSERT_BATCH = 128        # 32MB limitine takılmamak için

MODEL_NAME = "BAAI/bge-m3"
QDRANT_REQUEST_TIMEOUT = 120.0
UPSERT_MAX_RETRIES = 5
UPSERT_BACKOFF_BASE = 2.0

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


def sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

def make_point_id(m: Dict[str, Any]) -> int:
    """Deterministik 64-bit int ID."""
    base = f"{m.get('doc_id','')}|{m.get('section','')}|{m.get('text_sha1','')}"
    # SHA1'den ilk 16 hex = 64-bit integer
    return int(hashlib.sha1(base.encode("utf-8")).hexdigest()[:16], 16)

def safe_list(x: Any) -> List:
    if not x:
        return []
    return x if isinstance(x, list) else [x]

def chunk_text(txt: str, size: int = CHUNK_CHAR, overlap: int = CHUNK_OVERLAP) -> List[Tuple[int,int,str]]:
    txt = (txt or "").strip()
    n = len(txt)
    if n == 0:
        return []
    if n <= size:
        return [(0, n, txt)]
    out: List[Tuple[int,int,str]] = []
    step = max(1, size - overlap)
    i = 0
    while i < n:
        piece = txt[i:i+size]
        if not piece: break
        out.append((i, i+len(piece), piece))
        i += step
    return out

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
    if torch.cuda.is_available():
        try:
            print("CUDA GPU:", torch.cuda.get_device_name(0))
        except Exception:
            print("CUDA kullanılabilir.")
        try:
            torch.set_float32_matmul_precision("high")
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        except Exception:
            pass
        return "cuda"
    print("CUDA bulunamadı, CPU kullanılacak.")
    return "cpu"

@dataclass
class ChunkPack:
    idx: int
    next_line_after: int
    records: List[str]
    metas: List[Dict[str,Any]]

def process_and_upload_chunk(model: SentenceTransformer,
                             client: QdrantClient,
                             pack: ChunkPack) -> None:
    recs, metas = pack.records, pack.metas
    print(f"[Embed] Chunk {pack.idx} starting | segments={len(recs)}")

    if not recs:
        emb = np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
    else:
        all_embeddings = []
        bs = EMB_BATCH_SIZE
        i = 0
        while i < len(recs):
            try:
                batch_texts = recs[i:i+bs]
                e = model.encode(batch_texts, batch_size=bs, normalize_embeddings=True, show_progress_bar=False)
                all_embeddings.append(e)
                i += bs
            except RuntimeError as ex:
                if "CUDA out of memory" in str(ex) and bs > 4:
                    bs = max(4, bs // 2)
                    print(f"[Embed] OOM yakalandı, batch size {bs} yapıldı, devam...")
                    torch.cuda.empty_cache()
                    continue
                raise
        emb = np.vstack(all_embeddings) if all_embeddings else np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)

    print(f"[Upload] Chunk {pack.idx} starting | vectors={emb.shape[0] if emb is not None else 0}")
    total = emb.shape[0]
    for s in tqdm(range(0, total, QDRANT_UPSERT_BATCH), desc=f"Chunk {pack.idx} Qdrant upload"):
        vecs = emb[s:s+QDRANT_UPSERT_BATCH]
        meta_slice = metas[s:s+QDRANT_UPSERT_BATCH]
        points: List[rest.PointStruct] = []
        for m_payload, v in zip(meta_slice, vecs):
            pid = make_point_id(m_payload)  # <- gRPC uyumlu int64 ID
            points.append(rest.PointStruct(id=pid, vector=v.tolist(), payload=m_payload))
        upsert_with_retry(client, points)

    print(f"[Upload] Chunk {pack.idx} done")

    # (Opsiyonel) upload başarılıysa geçici dosyaları sil
    if SAVE_TEMP_FILES:
        try:
            (OUT_DIR / f"embeddings_chunk_{pack.idx}.npy").unlink(missing_ok=True)
            (OUT_DIR / f"metadata_chunk_{pack.idx}.jsonl").unlink(missing_ok=True)
        except Exception:
            pass

def main():
    device = pick_device()
    print(f"→ Using device: {device}")

    # model
    model = SentenceTransformer(MODEL_NAME, device=device)
    vector_size = model.get_sentence_embedding_dimension()

    # qdrant (gRPC)
    client = QdrantClient(
        host=QDRANT_HOST, port=QDRANT_PORT,
        grpc_port=QDRANT_GRPC_PORT, prefer_grpc=True,
        timeout=QDRANT_REQUEST_TIMEOUT,
    )
    _ = client.get_collections()  # health check

    # state & collection
    state = load_state()
    ensure_collection(client, vector_size, state)
    next_line = state.get("next_line", 0)
    chunk_idx = state.get("chunk_idx", 0)
    print(f"▶ Resuming from line {next_line}, chunk {chunk_idx}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records: List[str] = []
    metas: List[Dict[str,Any]] = []
    lines_in_chunk = 0

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                if line_idx < next_line:
                    continue

                rec = json.loads(line)

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

if __name__ == "__main__":
    main()
