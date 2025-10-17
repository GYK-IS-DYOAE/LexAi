# src/retrieval/index_opensearch.py
import json
from pathlib import Path
from typing import Any, Dict, List

from opensearchpy import OpenSearch, helpers

INPUT_FILE = "data/interim/balanced_total30k.jsonl"
INDEX_NAME = "lexai_cases"

OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200

BATCH_SIZE = 1000
VERIFY_CERTS = False

client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    scheme="http",
    use_ssl=False,
    verify_certs=VERIFY_CERTS,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
    timeout=60,
)

def _as_list(x):
    if not x:
        return []
    if isinstance(x, list):
        return [s for s in x if isinstance(s, str) and s.strip()]
    if isinstance(x, str) and x.strip():
        return [x]
    return []

def _norm_laws(kanun_atiflari: List[Dict[str, Any]] | None) -> List[str]:
    out = []
    for k in kanun_atiflari or []:
        law = (k.get("kanun") or "").strip().upper()
        art = (k.get("madde") or "").strip()
        fik = (k.get("fikra") or "").strip()
        if law == "IK":
            law = "İŞ KANUNU"
        if law in ("4857", "6100"):
            law = "İŞ KANUNU" if law == "4857" else "HMK"
        if law and art:
            out.append(f"{law} {art}" + (f"/{fik}" if fik else ""))
        elif law:
            out.append(law)
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            uniq.append(t); seen.add(t)
    return uniq

def build_full_text(rec: Dict[str, Any]) -> str:
    doc_id = rec.get("doc_id")
    dava = rec.get("dava_turu")
    sonuc = rec.get("sonuc")
    esas = ", ".join(_as_list(rec.get("metin_esas_no")))
    karar_no = ", ".join(_as_list(rec.get("metin_karar_no")))
    gerekce = " ".join(_as_list(rec.get("gerekce")))
    hikaye = " ".join(_as_list(rec.get("hikaye")))
    karar_kisa = rec.get("karar") or ""
    karar_full = rec.get("karar_metni") or ""

    steps = []
    for a in rec.get("adimlar") or []:
        if isinstance(a, dict) and a.get("ozet"):
            steps.append(a["ozet"])
        elif isinstance(a, str):
            steps.append(a)
    steps_t = " • ".join([s for s in steps if s])

    laws = _norm_laws(rec.get("kanun_atiflari"))

    blocks = [
        f"[DOC] {doc_id}" if doc_id else None,
        f"[DAVA_TURU] {dava}" if dava else None,
        f"[SONUC] {sonuc}" if sonuc else None,
        f"[ESAS_NO] {esas}" if esas else None,
        f"[KARAR_NO] {karar_no}" if karar_no else None,
        f"[HIKAYE] {hikaye}" if hikaye else None,
        f"[GEREKCE] {gerekce}" if gerekce else None,
        f"[KARAR] {karar_kisa}" if karar_kisa else None,
        f"[KARAR_METNI] {karar_full}" if karar_full else None,
        f"[ADIMLAR] {steps_t}" if steps_t else None,
        f"[KANUNLAR] {'; '.join(laws)}" if laws else None,
    ]
    return "\n".join([b for b in blocks if b])

def ensure_index():
    if client.indices.exists(index=INDEX_NAME):
        client.indices.delete(index=INDEX_NAME)

    settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "tr_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                },
                "normalizer": {
                    "lower_norm": {
                        "type": "custom",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword", "normalizer": "lower_norm"},
                "dava_turu": {
                    "type": "text", "analyzer": "tr_analyzer",
                    "fields": {"kw": {"type": "keyword", "normalizer": "lower_norm"}},
                    "copy_to": ["full_text"]
                },
                "sonuc": {"type": "keyword", "normalizer": "lower_norm"},
                "metin_esas_no": {"type": "keyword", "normalizer": "lower_norm"},
                "metin_karar_no": {"type": "keyword", "normalizer": "lower_norm"},

                "laws_norm": {
                    "type": "text", "analyzer": "tr_analyzer",
                    "fields": {"kw": {"type": "keyword", "normalizer": "lower_norm"}},
                    "copy_to": ["full_text"]
                },

                "gerekce": {"type": "text", "analyzer": "tr_analyzer", "copy_to": ["full_text"]},
                "karar":   {"type": "text", "analyzer": "tr_analyzer", "copy_to": ["full_text"]},
                "hikaye":  {"type": "text", "analyzer": "tr_analyzer", "copy_to": ["full_text"]},

                "karar_metni_raw": {"type": "text", "analyzer": "tr_analyzer"},  # tam metin (UI doğrudan çeker)
                "full_text": {"type": "text", "analyzer": "tr_analyzer"}
            }
        }
    }
    client.indices.create(index=INDEX_NAME, body=settings)

def gen_actions(docs_iter):
    for i, rec in enumerate(docs_iter):
        _id = str(rec.get("doc_id") or f"auto_{i}")
        laws = _norm_laws(rec.get("kanun_atiflari"))
        full_text = build_full_text(rec)
        src = {
            "doc_id": rec.get("doc_id"),
            "dava_turu": rec.get("dava_turu"),
            "sonuc": rec.get("sonuc"),
            "metin_esas_no": rec.get("metin_esas_no"),
            "metin_karar_no": rec.get("metin_karar_no"),

            "laws_norm": laws,

            "gerekce": rec.get("gerekce"),
            "karar": rec.get("karar"),
            "hikaye": rec.get("hikaye"),

            "karar_metni_raw": rec.get("karar_metni") or rec.get("karar") or "",
            "full_text": full_text
        }
        yield {"_index": INDEX_NAME, "_id": _id, "_source": src}

def main():
    docs_path = Path(INPUT_FILE)
    if not docs_path.exists():
        raise FileNotFoundError(f"Girdi dosyası bulunamadı: {INPUT_FILE}")

    ensure_index()

    with open(docs_path, "r", encoding="utf-8") as f:
        helpers.bulk(client, gen_actions(json.loads(line) for line in f),
                     chunk_size=BATCH_SIZE, request_timeout=180)

    count = client.count(index=INDEX_NAME)["count"]
    print(f"Indexed documents: {count}")

if __name__ == "__main__":
    main()
