# qdrant_quickcheck.py
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

COLL = "lexai_cases"

# 1) HTTP kullan (gRPC sorun çıkarıyorsa uğraşmayalım), timeout uzun tut
c = QdrantClient(host="localhost", port=6333, prefer_grpc=False, timeout=180.0)

# 2) toplam (genel) sayım
total = c.count(COLL, exact=True).count
print("Toplam vektör:", total)

# 3) 'section' filtresi örneği için index kurmayı dene (varsa geçer)
try:
    c.create_payload_index(COLL, field_name="section", field_schema=rest.PayloadSchemaType.KEYWORD)
    print("Index ok: section")
except Exception:
    pass

# 4) hızlı scroll: önce filtresiz 2 örnek, sonra gerekce filtresiyle 2 örnek
def scroll_any(limit=2, filt=None):
    try:
        pts, off = c.scroll(COLL, limit=limit, with_payload=True, with_vectors=False, filter=filt)
    except TypeError:
        pts, off = c.scroll(COLL, limit=limit, with_payload=True, with_vectors=False, scroll_filter=filt)
    return pts, off

print("\n--- SCROLL (filtresiz, 2 örnek) ---")
pts, off = scroll_any(limit=2, filt=None)
for p in pts:
    pl = p.payload or {}
    print(p.id, pl.get("section"), (pl.get("text_preview") or "")[:120])

flt = rest.Filter(must=[rest.FieldCondition(key="section", match=rest.MatchValue(value="gerekce"))])

print("\n--- SCROLL (section=gerekce, 2 örnek) ---")
pts, off = scroll_any(limit=2, filt=flt)
for p in pts:
    pl = p.payload or {}
    print(p.id, pl.get("section"), (pl.get("text_preview") or "")[:120])

# 5) basit semantik arama: önce filtresiz, sonra section=gerekce ile
model = SentenceTransformer("BAAI/bge-m3", device="cpu")
q = "kira sözleşmesinin feshi ve tahliye"
qvec = model.encode([q], normalize_embeddings=True)[0].tolist()

def search_any(qvec, limit=5, filt=None):
    """Önce yeni query_points imzasını dener; olmazsa eski search'e düşer."""
    try:
        # Yeni API bazı sürümlerde filter/params isimleriyle
        res = c.query_points(
            collection_name=COLL,
            query=[qvec],
            limit=limit,
            filter=filt,
            with_payload=True,
            params=rest.SearchParams(hnsw_ef=128, exact=False),
            timeout=180.0,
        )
        points = res[0].points
        return [(p.score, p.id, p.payload) for p in points]
    except AssertionError:
        # Eski API imzası: query_filter + search_params
        hits = c.search(
            collection_name=COLL,
            query_vector=qvec,
            limit=limit,
            with_payload=True,
            search_params=rest.SearchParams(hnsw_ef=128, exact=False),
            query_filter=filt,
            timeout=180.0,
        )
        return [(h.score, h.id, h.payload) for h in hits]

print("\n--- SEARCH (filtresiz, top-5) ---")
for sc, pid, pl in search_any(qvec, limit=5, filt=None):
    print(round(sc,4), pid, (pl.get("section") if pl else None), ((pl or {}).get("text_preview") or "")[:120])

print("\n--- SEARCH (section=gerekce, top-5) ---")
for sc, pid, pl in search_any(qvec, limit=5, filt=flt):
    print(round(sc,4), pid, (pl.get("section") if pl else None), ((pl or {}).get("text_preview") or "")[:120])
