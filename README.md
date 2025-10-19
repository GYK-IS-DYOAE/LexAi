# ⚖️ LexAI — Yapay Zeka Destekli Hukuk Asistanı (Monorepo)

LexAI, Türkçe yargı kararları ve mevzuat üzerinde **hybrid arama (OpenSearch + Qdrant)** ve **RAG** (Retrieval-Augmented Generation) yaklaşımıyla çalışan; **FastAPI** tabanlı bir backend ve **Vite + React + TypeScript** tabanlı bir frontend içeren **modüler** bir LegalTech projesidir.  
Bu repo, hem backend (FastAPI) hem de frontend’i (React-TS) birlikte barındırır.

---

## 1) Proje Özeti

### Amaç
- **Admin panelinde kullanıcı yönetimi** ve **sohbet geri bildirimlerinin listelenmesi/incelemesi**
- **Benzer dava önerileri**, mevzuat bağlantıları ve kaynaklı **RAG cevapları**

### Stack
- **Frontend (FE)**: Vite + React + TypeScript, TailwindCSS, shadcn-ui (elle eklenmiş bileşenler), `vite-tsconfig-paths` ile alias: `@/*`
- **Backend (BE)**: FastAPI, SQLAlchemy, Pydantic, JWT Auth
- **Retrieval**: OpenSearch (anahtar kelime) + Qdrant (vektör benzerlik) + SentenceTransformers (BGE-M3/Legal encoder)
- **LLM**: Ollama (`qwen2.5:7b-instruct`, `llama3`, `mistral`)
- **DB**: PostgreSQL



## 2) RAG Akışı

1. **Ön işleme** → `process_user_query`: sorguyu temizler ve zenginleştirir  
2. **Hybrid Retrieval** → `retrieve_combined.py`: OpenSearch + Qdrant sonuçlarını birleştirir, **MMR** ile dengeler  
3. **Prompt** → `prompt_builder.py`: seçilen pasajları LLM'e uygun biçimde birleştirir  
4. **LLM Yanıtı** → `query_llm.py`: Ollama (`/api/generate`) ile gerekçeli, kaynaklı yanıt üretir  
5. **Doğrulama** → `validators/`: metin kontrolü ve kaynak biçimleme  
6. **Kayıt & Feedback** → yanıt ve kullanıcı geri bildirimi DB’ye kaydedilir; ETL ile `feedback.jsonl → sft_data.jsonl`

---

## 3) Kurulum ve Çalıştırma

### A. Geliştirme Ortamı (Local)

### Backend

`cd LexAi-Backend`
`python -m venv .venv`
#### Windows:
`.venv\Scripts\activate`
#### Linux/Mac:
 `source .venv/bin/activate`

`pip install -r requirements.txt`

#### Postgres
POSTGRES_USER=***
POSTGRES_PASSWORD=***
POSTGRES_DB=lexai_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

#### Vector / Search
QDRANT_HOST=localhost
QDRANT_PORT=6333
OS_HOST=localhost
OS_PORT=9200

#### Ollama
OLLAMA_HOST=http://localhost:11434

#### Auth
JWT_SECRET_KEY=change_me
ACCESS_TOKEN_EXPIRE_MINUTES=1440

#### Veritabanını başlat 
`python -m src.core.init_db` Uvicorn ile çalıştır 
`vicorn src.main:app --reload --port 8000` # Swagger: http://localhost:8000/docs Frontend


### Frontend

`cd ../LexAi-Frontend`

`npm install`
`npm run dev`
#### http://localhost:5173
lib/api.ts içinde baseURL ve token ekleme örneği:

import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
B. Docker (Yerel ya da Sunucu)
Öneri: docker-compose.yml içine postgres, qdrant, opensearch, ollama, backend, frontend servislerini ekle.
OpenSearch için Linux’ta:

sudo sysctl -w vm.max_map_count=262144

###Ollama modelleri:

ollama pull qwen2.5:7b-instruct
#### opsiyonel:
#### ollama pull llama3
#### ollama pull mistral

---

## 4) Embedding ve İndeksleme (Retrieval Hazırlığı)

1) Embedding üret
#### veriyi oku (örn. data/interim/*.jsonl) → Qdrant’a gönder
python -m src.retrieval.vector_embedding

2) OpenSearch indeksle
python -m src.retrieval.index_opensearch

3) Hybrid test
python -m src.retrieval.retrieve_combined --query "işe iade davası"
Not: src/rag/config.py içindeki EMBED_MODEL_NAME, TOP_K_OS, TOP_K_QDRANT, MMR_LAMBDA ve servis host/port değerlerini projene göre ayarla.

---

## 5) API Uçları (Özet)
Yöntem	Yol	Açıklama	Auth
POST	/auth/register	Kullanıcı kaydı	
POST	/auth/login	JWT token al	
GET	/users/me	Aktif kullanıcı	
POST	/ask	RAG cevabı üret	
POST	/feedback	Geri bildirim oluştur	
GET	/similar_cases	Benzer dava listesi	

Örnek:
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@lexai.ai","password":"secret"}'

---

## 6) Admin Paneli (FE)
UserList.tsx: Kullanıcıları listeler (rol, e-posta, oluşturulma tarihi…).

-FeedbackList.tsx: Sohbet geri bildirimlerini listeler/inceletir.

-AdminPanel.tsx: Üst seviye panel; modül linkleri ve sayaçlar.

-PrivateLayout.tsx: Yetkili görünümü; sabit sidebar + üst bar.

-SideBar.tsx: Chat, Benzer Davalar, Admin ve Ayarlar hızlı erişim.

-ThemeToggle.tsx: Koyu/açık tema.

---

## 7) Güvenlik ve Kimlik Doğrulama
**JWT**: /auth/login dönen token’ı localStorage’da tut; tüm isteklerde Authorization: Bearer <token>.

**Role**: user, admin gibi rollerle Admin paneline erişim kısıtlanır.

**CORS**: FE/BE farklı origin ise CORSMiddleware ayarlı olmalı.

---

## 8) Dağıtım (Ubuntu 22.04 LTS Öneri)
Gereksinimler

sudo apt update
sudo apt install -y docker.io docker-compose nginx
sudo sysctl -w vm.max_map_count=262144
Env: .env dosyalarını doldur; docker-compose up -d.

Reverse Proxy: Nginx server_name domainine yönlendir; HTTPS için Certbot.

Kalıcı Veri: volumes: ile postgres_data, qdrant_data, os_data, ollama_models gibi persistent volume’lar.

Güncelleme: Zero-downtime için docker-compose pull && docker-compose up -d.

---

## 9) Sorun Giderme
OpenSearch max virtual memory areas vm.max_map_count:

sudo sysctl -w vm.max_map_count=262144
Qdrant bağlantı: 6333/6334 (REST/GRPC) portları açık mı, host doğru mu?

Ollama model yok: ollama list ile kontrol; yoksa ollama pull <model>.

JWT 401: FE’de token interceptor çalışıyor mu? Authorization başlığı gidiyor mu?

SQLAlchemy first()/session hataları: DB oturumu Depends(get_db) ile her istek için açılıp kapanıyor mu?

CORS: FE domaini allow_origins’te listeli mi?

---

## 10) Geliştirme İpuçları
Windows/WSL: OpenSearch için vm.max_map_count WSL’de de gerekir.

State/Logs: data/processed/embeddings/state.json gibi dosyalar embed ilerlemesini tutar.

MMR: MMR_LAMBDA değerini 0.1–0.7 aralığında test et; çeşitlilik/ilişkililik dengesi.

Chunking: MAX_PASSAGE_CHARS ile pasaj uzunluğunu hataya düşmeyecek şekilde sınırla.

Prompt: prompt_builder.py yanıt biçimini kullanıcı-dostu yapar; JSON değil, doğal metin.

---

## 11) Lisans
**MIT License © 2025 — LexAI.**
Bu yazılım hukuki danışmanlık yerine geçmez; yalnızca destek amaçlıdır.


---

<img width="1513" height="891" alt="1 1" src="https://github.com/user-attachments/assets/2b29b1c9-7e8e-41cb-955b-9ceb686a28f0" />
<img width="1524" height="868" alt="2" src="https://github.com/user-attachments/assets/368227e0-912a-4998-8ba3-296b837af437" />
<img width="1520" height="871" alt="3" src="https://github.com/user-attachments/assets/fbea7a03-b360-4882-a975-132750cab9dc" />
<img width="1490" height="899" alt="4" src="https://github.com/user-attachments/assets/322f12fc-64b3-4dfc-965e-8452c4e94cdc" />
<img width="1490" height="894" alt="7" src="https://github.com/user-attachments/assets/f5dfe6ad-e0d7-4341-90af-d4a514fff0d8" />
<img width="1486" height="889" alt="6" src="https://github.com/user-attachments/assets/273e7a2b-1bdd-469f-bd50-def86eef9440" />
<img width="1482" height="900" alt="5" src="https://github.com/user-attachments/assets/dc5a4a2f-04c5-4b83-bdfb-3ec9b53a76a2" /> 


