# src/retrieval/index_opensearch.py
# ==========================================================
# Karar verilerini OpenSearch'e indeksleme (BM25 keyword arama için)
# ==========================================================

import json
from opensearchpy import OpenSearch, helpers
from tqdm import tqdm
from pathlib import Path

# ============================== Config ==============================
INPUT_FILE = "data/interim/balanced_total30k.jsonl"
INDEX_NAME = "lexai_cases"

OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200

BATCH_SIZE = 500  # önerilen
VERIFY_CERTS = False

# ============================== Connect ==============================
client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    scheme="http",            # ✅ HTTP çünkü security kapalı
    use_ssl=False,            # ✅ TLS yok
    verify_certs=VERIFY_CERTS,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
    timeout=60
)

# ============================== Index Reset ==============================
if client.indices.exists(index=INDEX_NAME):
    print(f"⚠️  Index '{INDEX_NAME}' already exists → deleting...")
    client.indices.delete(index=INDEX_NAME)

settings = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "turkish_text": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "doc_id": {"type": "keyword"},
            "dava_turu": {"type": "text", "analyzer": "turkish_text"},
            "taraf_iliskisi": {"type": "text", "analyzer": "turkish_text"},
            "sonuc": {"type": "text", "analyzer": "turkish_text"},
            "metin_esas_no": {"type": "keyword"},
            "metin_karar_no": {"type": "keyword"},
            "kanun_atiflari": {"type": "nested"},
            "onemli_tarihler": {"type": "nested"},
            "karar": {"type": "text", "analyzer": "turkish_text"},
            "gerekce": {"type": "text", "analyzer": "turkish_text"},
            "hikaye": {"type": "text", "analyzer": "turkish_text"}
        }
    }
}

client.indices.create(index=INDEX_NAME, body=settings)
print(f"✅ Created index '{INDEX_NAME}'")

# ============================== Load & Bulk Insert ==============================
docs_path = Path(INPUT_FILE)
if not docs_path.exists():
    raise FileNotFoundError(f"Girdi dosyası bulunamadı: {INPUT_FILE}")

docs = []
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 1000:
            break
        rec = json.loads(line)
        _id = str(rec.get("doc_id") or f"auto_{i}")
        docs.append({"_id": _id, "_source": rec})

print(f"✅ Loaded {len(docs)} docs for test insert")

def gendata():
    for d in docs:
        yield {
            "_index": INDEX_NAME,
            "_id": d["_id"],
            "_source": d["_source"]
        }

print("⚙️  Bulk inserting...")
helpers.bulk(client, gendata(), chunk_size=BATCH_SIZE, request_timeout=120)
print("🎉 Test data inserted into OpenSearch successfully!")

# ============================== Sanity Check ==============================
count = client.count(index=INDEX_NAME)["count"]
print(f"📊 Indexed documents: {count}")
