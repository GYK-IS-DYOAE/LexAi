"""
config.py
---------
Tüm servis ayarları tek yerde. Üretim/deneme profillerinde pratik olur.
python src/retrieval/retrieve_combined.py "nafaka" --topn 8
"""

# OpenSearch
OS_HOST = "localhost"
OS_PORT = 9200
OS_USER = None           # ❌ security kapalı → şifre yok
OS_PASS = None           # ❌ security kapalı → şifre yok
OS_INDEX = "lexai_cases"

# Qdrant
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "lexai_cases"

# Embedding modeli (lokal encode)
EMBED_MODEL_NAME = "BAAI/bge-m3"

# Hibrit parametreleri
TOP_K_OS = 50
TOP_K_QDRANT = 50
MMR_LAMBDA = 0.5
DEFAULT_TOPN = 8

# Prompt/Yanıt uzunlukları
MAX_PASSAGE_CHARS = 1200   # her pasaj kırpma
MAX_TOTAL_PASSAGES = 8     # LLM'e giden pasaj sayısı
