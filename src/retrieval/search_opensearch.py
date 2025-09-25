import sys
from opensearchpy import OpenSearch

"""
search_opensearch.py
-------------------
Amaç:
- OpenSearch içinde indekslenmiş karar verilerinde BM25 tabanlı arama yapmak.
- Kullanıcının verdiği sorguyu (ör. "ziynet alacağı") dava_turu, taraf_iliskisi,
  sonuc, karar, gerekce, hikaye alanlarında aratır.

Girdi:
- Komut satırından sorgu (örn: "ziynet alacağı")

Çıktı:
- İlk 5 sonucun doc_id, dava_turu, sonuc, metin_karar_no bilgileri

Bağımlılıklar:
- Python paketleri: opensearch-py
- Docker: OpenSearch’in çalışıyor olması gerekir.
  👉 Başlatmak için:
     $ docker start opensearch
  veya ilk kez kurulum için:
     $ docker run -d --name opensearch -p 9200:9200 -p 9600:9600 \
       -e "discovery.type=single-node" \
       -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=Lexai_1234!" \
       opensearchproject/opensearch:2.15.0

Nasıl çalıştırılır:
$ python scripts/search_opensearch.py "ziynet alacağı"
"""

# ==============================
# Config
# ==============================
INDEX_NAME = "lexai_cases"
OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200
USERNAME = "admin"
PASSWORD = "Lexai_1234!"   # Docker başlatırken verdiğin şifre

# ==============================
# Connect
# ==============================
client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    http_auth=(USERNAME, PASSWORD),
    use_ssl=True,          # ✅ HTTPS
    verify_certs=False,    # test için self-signed cert kontrol etme
    ssl_show_warn=False
)

# ==============================
# Search
# ==============================
def search(query):
    body = {
        "size": 5,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["dava_turu", "taraf_iliskisi", "sonuc", "karar", "gerekce", "hikaye"]
            }
        }
    }
    results = client.search(index=INDEX_NAME, body=body)
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_opensearch.py '<query>'")
        sys.exit(1)

    query = sys.argv[1]
    print(f"\n🔎 Query: {query}\n")
    results = search(query)

    for i, hit in enumerate(results["hits"]["hits"], 1):
        src = hit["_source"]
        print(f"{i}. (score={hit['_score']:.4f})")
        print(f"   doc_id: {src.get('doc_id')}")
        print(f"   dava_turu: {src.get('dava_turu')}")
        print(f"   sonuc: {src.get('sonuc')}")
        print(f"   metin_karar_no: {src.get('metin_karar_no')}")
        print()
