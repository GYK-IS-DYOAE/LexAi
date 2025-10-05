"""
config.py
---------
Tüm servis ayarları tek yerde. Üretim/deneme profillerinde pratik olur.
python src/retrieval/retrieve_combined.py "nafaka" --topn 8

"""

OS_HOST = "localhost"
OS_PORT = 9200
OS_USER = "admin"
OS_PASS = "Lexai_1234!"
OS_INDEX = "lexai_cases"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "lexai_cases"

# Embedding modeli sadece retrieval ve MMR için kullanılıyor (lokal encode)
EMBED_MODEL_NAME = "BAAI/bge-m3"

# Ollama / Qwen Instruct
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b-instruct"

# Hibrit parametreleri
TOP_K_OS = 50
TOP_K_QDRANT = 50
MMR_LAMBDA = 0.5
DEFAULT_TOPN = 8

# Prompt/Yanıt uzunlukları
MAX_PASSAGE_CHARS = 1200   # her pasaj kırpma
MAX_TOTAL_PASSAGES = 8     # LLM'e giden pasaj sayısı
