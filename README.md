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

---

## 2) Monorepo Klasör Yerleşimi

LexAI/
├─ LexAi-Backend/
│  ├─ configs/
│  ├─ data/               
│  ├─ docs/
│  ├─ notebooks/
│  ├─ src/
│  │  ├─ api/
│  │  │  ├─ auth/           
│  │  │  ├─ conversation/  
│  │  │  ├─ feedback/      
│  │  │  └─ similar/         
│  │  ├─ core/               
│  │  ├─ etl/           
│  │  ├─ graph/           
│  │  ├─ llm/               
│  │  ├─ models/           
│  │  ├─ planner/           
│  │  ├─ rag/
│  │  │  ├─ config.py
│  │  │  ├─ prompt_builder.py
│  │  │  └─ query_llm.py
│  │  ├─ retrieval/
│  │  │  ├─ index_opensearch.py
│  │  │  ├─ retrieve_combined.py
│  │  │  ├─ search_opensearch.py
│  │  │  ├─ search_qdrant.py
│  │  │  └─ vector_embedding.py
│  │  ├─ services/         
│  │  ├─ user_input/       
│  │  ├─ validators/                   
│  │  └─ start_app.bat       
│  ├─ requirements.txt
│  └─ run_main.py            
└─ LexAi-Frontend/
   └─ src/
    ├─ app/
    │  ├─ providers.tsx
    │  └─ router.tsx
    ├─ components/
    │  ├─ common/
    │  │  └─ Modal.tsx              
    │  ├─ layout/
    │  │  ├─ AdminPanel.tsx
    │  │  ├─ PrivateLayout.tsx
    │  │  ├─ SideBar.tsx
    │  │  └─ ThemeToggle.tsx
    │  └─ ui/                        
    │     ├─ avatar.tsx
    │     ├─ badge.tsx
    │     ├─ button.tsx              
    │     ├─ card.tsx                
    │     ├─ dialog.tsx              
    │     ├─ input.tsx
    │     ├─ label.tsx
    │     └─ separator.tsx
    ├─ features/
    │  └─ admin/
    │     ├─ UserList.tsx           
    │     └─ FeedbackList.tsx        
    ├─ lib/
    │  └─ api.ts                     
    ├─ assets/...
    ├─ landing/...
    └─ home/...

## 5) RAG Akışı

1. **Ön işleme** → `process_user_query`: sorguyu temizler ve zenginleştirir  
2. **Hybrid Retrieval** → `retrieve_combined.py`: OpenSearch + Qdrant sonuçlarını birleştirir, **MMR** ile dengeler  
3. **Prompt** → `prompt_builder.py`: seçilen pasajları LLM'e uygun biçimde birleştirir  
4. **LLM Yanıtı** → `query_llm.py`: Ollama (`/api/generate`) ile gerekçeli, kaynaklı yanıt üretir  
5. **Doğrulama** → `validators/`: metin kontrolü ve kaynak biçimleme  
6. **Kayıt & Feedback** → yanıt ve kullanıcı geri bildirimi DB’ye kaydedilir; ETL ile `feedback.jsonl → sft_data.jsonl`

---

## 6) Kurulum ve Çalıştırma

### A. Geliştirme Ortamı (Local)

#### Backend
```bash
cd LexAi-Backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -r requirements.txt

### `.env` (örnek)
```env
# Postgres
POSTGRES_USER=lexai
POSTGRES_PASSWORD=lexai123
POSTGRES_DB=lexai_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Vector / Search
QDRANT_HOST=localhost
QDRANT_PORT=6333
OS_HOST=localhost
OS_PORT=9200

# Ollama
OLLAMA_HOST=http://localhost:11434

# Auth
JWT_SECRET_KEY=change_me
ACCESS_TOKEN_EXPIRE_MINUTES=1440


Veritabanını başlat bash Kodu kopyala python -m src.core.init_db Uvicorn ile çalıştır bash Kodu kopyala uvicorn src.main:app --reload --port 8000 # Swagger: http://localhost:8000/docs Frontend

