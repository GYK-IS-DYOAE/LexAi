import re
import sys
from typing import List, Dict, Any
from opensearchpy import OpenSearch

INDEX_NAME = "lexai_cases"
OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200

client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    scheme="http",
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False,
)

LAW_PAT = re.compile(
    r"\b(?:(HMK|HUMK|TBK|TMK|İK|IK|İŞ\s*KANUNU|IS\s*KANUNU|4857|6100))\s*(\d{1,3})?(?:\s*/\s*(\d{1,2}))?",
    flags=re.IGNORECASE,
)

def _detect_laws(q: str) -> List[str]:
    out: List[str] = []
    for m in LAW_PAT.finditer(q or ""):
        code = (m.group(1) or "").upper().replace("IS", "İŞ").replace("IK", "İK")
        art = m.group(2) or ""
        fik = m.group(3) or ""
        if code in ("4857", "6100"):
            # 4857 → İş Kanunu, 6100 → HMK
            code = "İŞ KANUNU" if code == "4857" else "HMK"
        if code == "İK":
            code = "İŞ KANUNU"
        tag = code
        if art:
            tag += f" {art}"
        if fik:
            tag += f"/{fik}"
        out.append(tag)
    # benzersiz sırayı koru
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq

def build_query_body(user_query: str, size: int = 10) -> Dict[str, Any]:
    laws = _detect_laws(user_query)
    should_terms = []
    if laws:
        should_terms.append({"terms": {"laws_norm.kw": laws, "boost": 3}})

    body: Dict[str, Any] = {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": user_query,
                            "type": "best_fields",
                            "fields": [
                                "dava_turu^4",
                                "laws_norm^3",
                                "full_text^2",
                                # geri uyumluluk: eski alanlar varsa
                                "gerekce^2",
                                "karar^1.5",
                                "hikaye^1",
                            ],
                            "operator": "and",
                        }
                    }
                ],
                "should": should_terms,
            }
        },
    }
    return body

def search(query: str, size: int = 10) -> Dict[str, Any]:
    body = build_query_body(query, size=size)
    return client.search(index=INDEX_NAME, body=body)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.retrieval.search_opensearch '<query>' [size]")
        sys.exit(1)

    q = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"\nQuery: {q}\n")
    res = search(q, size=n)

    hits = res.get("hits", {}).get("hits", [])
    for i, h in enumerate(hits, 1):
        src = h.get("_source", {})
        score = h.get("_score", 0.0)
        doc_id = src.get("doc_id")
        dava_turu = src.get("dava_turu")
        sonuc = src.get("sonuc")
        laws = src.get("laws_norm") or src.get("kanunlar")
        preview = (
            src.get("text_preview")
            or src.get("full_text")
            or src.get("gerekce")
            or src.get("hikaye")
            or ""
        )
        if isinstance(preview, list):
            preview = " ".join(preview)
        print(f"{i}. score={score:.4f} doc_id={doc_id}")
        print(f"   dava_turu: {dava_turu} | sonuc: {sonuc}")
        if laws:
            if isinstance(laws, list):
                laws_str = ", ".join(laws)
            else:
                laws_str = str(laws)
            print(f"   laws: {laws_str}")
        if preview:
            pv = preview.strip().replace("\n", " ")
            if len(pv) > 160:
                pv = pv[:160] + "..."
            print(f"   preview: {pv}")
        print()

#python src\retrieval\search_opensearch.py "ziynet alacağı"