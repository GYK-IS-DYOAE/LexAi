import json
from pathlib import Path
from opensearchpy import OpenSearch, helpers
from tqdm import tqdm

"""
index_opensearch.py
-------------------
Amaç:
- Karar verilerini (records.jsonl) OpenSearch içine indekslemek.
- BM25 tabanlı arama yapılabilmesi için mapping ve bulk insert işlemleri yapmak.

Girdi:
- data/processed/records.jsonl

Çıktı:
- OpenSearch index: lexai_cases

Bağımlılıklar:
- Python paketleri: opensearch-py, tqdm
- Docker: OpenSearch’in çalışıyor olması gerekir.
  👉 OpenSearch başlatmak için:
     $ docker run -d --name opensearch -p 9200:9200 -p 9600:9600 \
       -e "discovery.type=single-node" \
       -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=Lexai_1234!" \
       opensearchproject/opensearch:2.15.0

Notlar:
- Kullanıcı adı: admin
- Şifre: Docker’da verdiğin `OPENSEARCH_INITIAL_ADMIN_PASSWORD`
- Mapping: dava_turu, taraf_iliskisi, sonuc, karar, gerekce, hikaye alanları `text`;
           metin_esas_no, metin_karar_no `keyword`; kanun_atiflari, onemli_tarihler `nested`.

Nasıl çalıştırılır:
$ python scripts/index_opensearch.py
"""

# ==============================
# Config
# ==============================
INPUT_FILE = "data/processed/records.jsonl"
INDEX_NAME = "lexai_cases"

OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200
USERNAME = "admin"
PASSWORD = "Lexai_1234!"   # Docker başlatırken verdiğin şifre

BATCH_SIZE = 1000   # bulk insert batch

# ==============================
# Connect OpenSearch (HTTPS)
# ==============================
client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    http_auth=(USERNAME, PASSWORD),
    scheme="https",          # ✅ HTTPS kullan
    use_ssl=True,            # ✅ SSL aç
    verify_certs=False       # self-signed sertifika için
)

# ==============================
# Create index (reset if exists)
# ==============================
if client.indices.exists(index=INDEX_NAME):
    client.indices.delete(index=INDEX_NAME)

settings = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    },
    "mappings": {
        "properties": {
            "doc_id": {"type": "keyword"},
            "dava_turu": {"type": "text"},
            "taraf_iliskisi": {"type": "text"},
            "sonuc": {"type": "text"},
            "metin_esas_no": {"type": "keyword"},
            "metin_karar_no": {"type": "keyword"},
            "kanun_atiflari": {"type": "nested"},
            "onemli_tarihler": {"type": "nested"},
            "karar": {"type": "text"},
            "gerekce": {"type": "text"},
            "hikaye": {"type": "text"}
        }
    }
}

client.indices.create(index=INDEX_NAME, body=settings)

# ==============================
# Load subset of data
# ==============================
docs = []
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 1000:  # sadece ilk 1000 kayıt test için
            break
        rec = json.loads(line)
        docs.append(rec)

print(f"✅ Loaded {len(docs)} docs for test insert")

# ==============================
# Bulk insert
# ==============================
def gendata():
    for rec in docs:
        yield {
            "_index": INDEX_NAME,
            "_id": rec["doc_id"],
            "_source": rec
        }

helpers.bulk(client, gendata(), chunk_size=BATCH_SIZE)
print("🎉 Test data inserted into OpenSearch successfully!")
