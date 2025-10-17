import json, time, hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

import numpy as np
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer, models
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

INPUT_FILE = "data/interim/balanced_total30k.jsonl"

OUT_DIR = Path("data/processed/embeddings")
STATE_FILE = OUT_DIR / "state.json"

COLLECTION_NAME = "lexai_cases"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_GRPC_PORT = 6334

CHUNK_SIZE_RECORDS = 3000
EMB_BATCH_SIZE = 32
QDRANT_UPSERT_BATCH = 128

# legal = msbayindir, bilkent = BERTurk-Legal, bge_m3 = BAAI/bge-m3 (1024-dim)
USE_MODEL = "bge_m3"
QDRANT_REQUEST_TIMEOUT = 120.0
UPSERT_MAX_RETRIES = 5
UPSERT_BACKOFF_BASE = 2.0

CHUNK_CHAR = 1500
CHUNK_OVERLAP = 100
MIN_CHAR = 40

SAVE_TEMP_FILES = False
STORE_FULL_TEXT_IN_QDRANT = False
TEXT_PREVIEW_CHARS = 200
DECISION_PREVIEW_CHARS = 1000
MAX_DECISION_META_CHARS = 12000
ENABLE_INT8_QUANTIZATION = True

def sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

def make_point_id(m: Dict[str, Any]) -> int:
    base = f"{m.get('doc_id','')}|{m.get('section','')}|{m.get('text_sha1','')}"
    return int(hashlib.sha1(base.encode("utf-8")).hexdigest()[:16], 16)

def safe_list(x: Any) -> List:
    if not x: return []
    return x if isinstance(x, list) else [x]

def chunk_text(txt: str, size: int = CHUNK_CHAR, overlap: int = CHUNK_OVERLAP) -> List[Tuple[int,int,str]]:
    txt = (txt or "").strip()
    n = len(txt)
    if n == 0: return []
    if n <= size: return [(0, n, txt)]
    out: List[Tuple[int,int,str]] = []
    step = max(1, size - overlap)
    i = 0
    while i < n:
        piece = txt[i:i+size]
        if not piece: break
        out.append((i, i+len(piece), piece))
        i += step
    return out

def _as_list(x):
    if not x: return []
    if isinstance(x, list): return [s for s in x if isinstance(s, str) and s.strip()]
    if isinstance(x, str) and x.strip(): return [x]
    return []

def _norm_laws(kanun_atiflari: List[Dict[str, Any]] | None) -> List[str]:
    out = []
    for k in kanun_atiflari or []:
        law = (k.get("kanun") or "").strip().upper()
        art = (k.get("madde") or "").strip()
        fik = (k.get("fikra") or "").strip()
        if law and art:
            out.append(f"{law} {art}" + (f"/{fik}" if fik else ""))
    return out

_KEY_HITS = ("bozma","onama","kabul","ret","görevsizlik","istinaf","temyiz","HMK","TBK","TMK","İş Kanunu","4857","6100")

def _pick_key_sentences(karar_metni: str, max_sent: int = 5) -> List[str]:
    if not karar_metni: return []
    sents = [s.strip() for s in karar_metni.replace("\n"," ").split(".") if s.strip()]
    scored = []
    for s in sents:
        score = sum(1 for k in _KEY_HITS if k.lower() in s.lower())
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:max_sent]]

def build_signal_text(rec: Dict[str, Any]) -> str:
    dava   = (rec.get("dava_turu") or "").strip()
    sonuc  = (rec.get("sonuc") or "").strip()
    gerek  = " ".join(_as_list(rec.get("gerekce")))[:1200]
    karar  = (rec.get("karar") or "")[:600]
    laws   = _norm_laws(rec.get("kanun_atiflari"))
    key_s  = _pick_key_sentences(rec.get("karar_metni") or "", 5)
    blocks = [
        f"[DAVA_TURU] {dava}" if dava else None,
        f"[SONUC] {sonuc}" if sonuc else None,
        f"[KANUNLAR] {'; '.join(laws)}" if laws else None,
        f"[GEREKCE_OZET] {gerek}" if gerek else None,
        f"[KARAR_OZET] {karar}" if karar else None,
        f"[KARAR_KILIT] {' '.join(key_s)}" if key_s else None,
    ]
    return "\n".join([b for b in blocks if b])

def add_signal_and_full(records: List[str], metas: List[Dict[str, Any]], rec: Dict[str, Any]) -> None:
    karar_full_all  = (rec.get("karar_metni") or rec.get("karar") or "").strip()
    karar_preview   = karar_full_all[:DECISION_PREVIEW_CHARS] if karar_full_all else None
    karar_full_trim = karar_full_all[:MAX_DECISION_META_CHARS] if karar_full_all else None

    # SIGNAL (tek nokta) → UI için tam metin payload'da
    signal_text = build_signal_text(rec).strip()
    if signal_text and len(signal_text) >= MIN_CHAR:
        payload = {
            "doc_id": rec.get("doc_id"),
            "section": "signal",
            "dava_turu": rec.get("dava_turu"),
            "sonuc": rec.get("sonuc"),
            "metin_esas_no": rec.get("metin_esas_no"),
            "metin_karar_no": rec.get("metin_karar_no"),
            "kanun_atiflari": rec.get("kanun_atiflari"),
            "laws_norm": _norm_laws(rec.get("kanun_atiflari")),
            "text_sha1": sha1(signal_text),
        }
        if not STORE_FULL_TEXT_IN_QDRANT:
            payload["text_preview"] = signal_text[:TEXT_PREVIEW_CHARS]
        else:
            payload["text"] = signal_text
        if karar_preview:    payload["karar_preview"] = karar_preview
        if karar_full_trim:  payload["karar_metni_meta"] = karar_full_trim
        if rec.get("karar"): payload["karar"] = rec.get("karar")

        records.append(signal_text)
        metas.append(payload)

    # DECISION FULL (dilimlenmiş) → arama için, büyük metni tekrar payload'a koyma
    decision_text = (rec.get("karar_metni") or rec.get("karar") or "").strip()
    if decision_text:
        for (_start, _end, piece) in chunk_text(decision_text, CHUNK_CHAR, CHUNK_OVERLAP):
            if len(piece.strip()) < MIN_CHAR: continue
            payload = {
                "doc_id": rec.get("doc_id"),
                "section": "decision_full",
                "dava_turu": rec.get("dava_turu"),
                "sonuc": rec.get("sonuc"),
                "metin_esas_no": rec.get("metin_esas_no"),
                "metin_karar_no": rec.get("metin_karar_no"),
                "kanun_atiflari": rec.get("kanun_atiflari"),
                "laws_norm": _norm_laws(rec.get("kanun_atiflari")),
                "text_sha1": sha1(piece),
            }
            if not STORE_FULL_TEXT_IN_QDRANT:
                payload["text_preview"] = piece[:TEXT_PREVIEW_CHARS]
            else:
                payload["text"] = piece
            if karar_preview: payload["karar_preview"] = karar_preview

            records.append(piece)
            metas.append(payload)

def optimize_torch_for_env():
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
        return SentenceTransformer("BAAI/bge-m3", device=device)
    else:
        raise ValueError("USE_MODEL 'legal' | 'bilkent' | 'bge_m3' olmalı")

def pick_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"

@dataclass
class ChunkPack:
    idx: int
    next_line_after: int
    records: List[str]
    metas: List[Dict[str,Any]]

def upsert_with_retry(client: QdrantClient, points: List[rest.PointStruct]) -> None:
    delay = 1.0
    for attempt in range(UPSERT_MAX_RETRIES):
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
            return
        except Exception as e:
            if attempt == UPSERT_MAX_RETRIES - 1: raise
            time.sleep(delay); delay *= UPSERT_BACKOFF_BASE

def process_and_upload_chunk(model: SentenceTransformer, client: QdrantClient, pack: ChunkPack) -> None:
    recs, metas = pack.records, pack.metas
    if not recs:
        emb = np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
    else:
        all_embeddings = []
        bs = EMB_BATCH_SIZE
        i = 0
        while i < len(recs):
            batch_texts = recs[i:i+bs]
            if torch.cuda.is_available():
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    e = model.encode(batch_texts, batch_size=bs, normalize_embeddings=True, show_progress_bar=False)
            else:
                e = model.encode(batch_texts, batch_size=bs, normalize_embeddings=True, show_progress_bar=False)
            all_embeddings.append(e); i += bs
        emb = np.vstack(all_embeddings) if all_embeddings else np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)

    total = emb.shape[0]
    for s in tqdm(range(0, total, QDRANT_UPSERT_BATCH), desc=f"Chunk {pack.idx} Qdrant upload"):
        vecs = emb[s:s+QDRANT_UPSERT_BATCH]
        meta_slice = metas[s:s+QDRANT_UPSERT_BATCH]
        points: List[rest.PointStruct] = []
        for m_payload, v in zip(meta_slice, vecs):
            pid = make_point_id(m_payload)
            points.append(rest.PointStruct(id=pid, vector=v.tolist(), payload=m_payload))
        upsert_with_retry(client, points)

def ensure_collection(client: QdrantClient, vector_size: int, state: Dict[str,Any]) -> None:
    exists = False
    try:
        info = client.get_collection(COLLECTION_NAME)
        current_dim = None
        try:
            current_dim = info.config.params.vectors.size
        except Exception:
            pass
        if current_dim != vector_size:
            client.delete_collection(COLLECTION_NAME)
            exists = False
        else:
            exists = True
    except Exception:
        exists = False

    if not exists:
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

    state["collection_ready"] = True
    save_state(state)

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

def main():
    p = Path(INPUT_FILE)
    if not p.exists():
        raise FileNotFoundError(f"INPUT_FILE not found: {p.resolve()}")

    if STATE_FILE.exists():
        STATE_FILE.unlink()

    device = pick_device()
    print(f"Using device: {device}")
    optimize_torch_for_env()
    model = load_embedding_model(device)
    vector_size = model.get_sentence_embedding_dimension()

    client = QdrantClient(
        host=QDRANT_HOST, port=QDRANT_PORT,
        grpc_port=QDRANT_GRPC_PORT, prefer_grpc=True,
        timeout=QDRANT_REQUEST_TIMEOUT,
    )
    _ = client.get_collections()

    state = load_state()
    ensure_collection(client, vector_size, state)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records: List[str] = []
    metas: List[Dict[str,Any]] = []
    lines_in_chunk = 0
    next_line = 0
    chunk_idx = 0

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                rec = json.loads(line)
                add_signal_and_full(records, metas, rec)

                lines_in_chunk += 1
                if lines_in_chunk == CHUNK_SIZE_RECORDS:
                    process_and_upload_chunk(
                        model, client,
                        ChunkPack(idx=chunk_idx, next_line_after=line_idx+1, records=records, metas=metas)
                    )
                    chunk_idx += 1
                    records, metas = [], []
                    lines_in_chunk = 0

            if lines_in_chunk > 0 and records:
                process_and_upload_chunk(
                    model, client,
                    ChunkPack(idx=chunk_idx, next_line_after=line_idx+1, records=records, metas=metas)
                )

    except KeyboardInterrupt:
        print("İşlem durduruldu.")
    except Exception as e:
        print(f"Hata: {e}")
        raise

if __name__ == "__main__":
    main()
