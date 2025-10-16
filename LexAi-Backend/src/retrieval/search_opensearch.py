# src/retrieval/search_opensearch.py
import sys
from opensearchpy import OpenSearch

INDEX_NAME = "lexai_cases"
OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200

client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    scheme="http",        
    use_ssl=False,        
    verify_certs=False,
    ssl_show_warn=False
)

def search(query):
    body = {
        "size": 5,
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "dava_turu", "taraf_iliskisi", "sonuc",
                    "karar", "gerekce", "hikaye"
                ]
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
        print(f"   metin: {src.get('hikaye')}")
        print()


#python src\retrieval\search_opensearch.py "ziynet alacağı"