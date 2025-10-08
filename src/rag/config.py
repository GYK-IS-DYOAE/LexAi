"""
config.py
---------
Tüm servis ve model ayarları bu dosyada toplanmıştır.
Retrieval (arama) ve LLM (cevap üretimi) bileşenleri için merkezi yapı sağlar.
"""

# ======================================
# 🔍 OpenSearch – Anahtar kelime arama
# ======================================
OS_HOST = "localhost"
OS_PORT = 9200
OS_USER = None      # Güvenlik kapalıysa kullanıcı/şifre boş kalır
OS_PASS = None
OS_INDEX = "lexai_cases"

# ======================================
# 🧠 Qdrant – Vektör (dense) arama
# ======================================
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "lexai_cases"

# ======================================
# ✨ Embedding Model (Retrieval için)
# ======================================
EMBED_MODEL_NAME = "BAAI/bge-m3"   # Sentence embedding modeli

# ======================================
# 🧾 Prompt & Cevap Ayarları
# ======================================
MAX_PASSAGE_CHARS = 1200           # Her pasajdan LLM'e en fazla kaç karakter verilecek
MAX_TOTAL_PASSAGES = 8             # LLM'e en fazla kaç pasaj gönderilecek

# ======================================
# ⚖️ Hibrit Arama Parametreleri
# ======================================
TOP_K_OS = 50                      # OpenSearch’ten kaç sonuç alınsın
TOP_K_QDRANT = 50                  # Qdrant’tan kaç sonuç alınsın
MMR_LAMBDA = 0.5                   # MMR denge katsayısı (0=çeşitlilik, 1=benzerlik)
DEFAULT_TOPN = 8                   # Kullanıcıya gösterilecek sonuç sayısı

# ======================================
# 🧠 LLM Ayarları (Cevap üretimi için)
# ======================================
LLM_BACKEND = "ollama"             # "ollama", "openai", "vllm" vb. olabilir
LLM_MODEL_NAME = "qwen:7b"         # Ollama'da yüklü model adı
LLM_BASE_URL = "http://localhost:11434"  # LLM API endpoint
LLM_TIMEOUT = 60                   # İstek zaman aşımı (saniye)
