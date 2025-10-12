# LexAI Main - Hukuk Asistanı

PostgreSQL ile entegre full-stack hukuk asistanı uygulaması.

## 🚀 Özellikler

- **Frontend**: React + Vite + Tailwind CSS
- **Backend**: FastAPI + PostgreSQL
- **Authentication**: JWT tabanlı kimlik doğrulama
- **Database**: PostgreSQL ile tam entegrasyon
- **API**: RESTful API endpoints
- **Search**: Hukuki arama sistemi
- **Admin Panel**: Sistem yönetimi

## 📋 Gereksinimler

### Sistem Gereksinimleri
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- npm/yarn

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Node.js Dependencies
```bash
cd frontend
npm install
```

## 🗄️ Veritabanı Kurulumu

### PostgreSQL Kurulumu
1. PostgreSQL'i yükleyin
2. Veritabanı oluşturun:
```sql
CREATE DATABASE lexai_main;
CREATE USER lexai_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE lexai_main TO lexai_user;
```

### Environment Variables
`.env` dosyası oluşturun:
```env
DATABASE_URL=postgresql://lexai_user:your_password@localhost:5432/lexai_main
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 🚀 Çalıştırma

### Otomatik Başlatma
```bash
# Windows
start_app.bat

# Linux/Mac
chmod +x start_app.sh
./start_app.sh
```

### Manuel Başlatma

#### Backend
```bash
cd LexAi-main
python run_main.py
```

#### Frontend
```bash
cd LexAi-main/frontend
npm run dev
```

## 🌐 Endpoints

### Frontend
- **Ana Sayfa**: http://localhost:3001
- **Giriş**: http://localhost:3001/login
- **Kayıt**: http://localhost:3001/register
- **Dashboard**: http://localhost:3001/dashboard

### Backend API
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Authentication**: http://localhost:8000/api/auth/*
- **Search**: http://localhost:8000/api/search
- **Admin**: http://localhost:8000/api/admin/*

## 👤 Varsayılan Kullanıcılar

### Admin Kullanıcı
- **Email**: admin@lexai.com
- **Password**: admin123
- **Yetki**: Tam admin yetkisi

## 🔧 Geliştirme

### Proje Yapısı
```
LexAi-main/
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/       # React bileşenleri
│   │   ├── App.jsx          # Ana uygulama
│   │   └── main.jsx         # Entry point
│   ├── package.json
│   └── vite.config.js
├── src/
│   ├── api/                 # FastAPI endpoints
│   │   ├── auth/            # Kimlik doğrulama
│   │   ├── search/          # Arama API
│   │   ├── feedback/        # Geri bildirim
│   │   └── rag/             # RAG sistemi
│   ├── core/                # Temel konfigürasyon
│   │   ├── db.py            # Veritabanı bağlantısı
│   │   └── init_db.py       # DB başlatma
│   └── models/              # Veritabanı modelleri
├── requirements.txt         # Python dependencies
├── run_main.py             # Ana başlatma scripti
└── start_app.bat           # Otomatik başlatma
```

### API Endpoints

#### Authentication
- `POST /api/auth/login` - Giriş yap
- `POST /api/auth/register` - Kayıt ol
- `GET /api/auth/me` - Kullanıcı bilgisi

#### Search
- `POST /api/search` - Hukuki arama
- `GET /api/admin/stats` - Sistem istatistikleri

#### Feedback
- `POST /api/feedback` - Geri bildirim gönder
- `GET /api/feedback` - Geri bildirimleri listele

## 🐛 Sorun Giderme

### Yaygın Sorunlar

1. **PostgreSQL Bağlantı Hatası**
   - PostgreSQL servisinin çalıştığından emin olun
   - Veritabanı URL'sini kontrol edin
   - Kullanıcı yetkilerini kontrol edin

2. **Frontend Bağlantı Hatası**
   - Backend'in çalıştığından emin olun
   - CORS ayarlarını kontrol edin
   - Port çakışmalarını kontrol edin

3. **Authentication Hatası**
   - JWT secret key'i kontrol edin
   - Token süresini kontrol edin
   - Kullanıcı veritabanını kontrol edin

### Log Dosyaları
- Backend logları: Terminal çıktısı
- Frontend logları: Browser console
- Database logları: PostgreSQL log dosyaları

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun
3. Değişikliklerinizi commit edin
4. Branch'inizi push edin
5. Pull Request oluşturun

## 📞 İletişim

- **Email**: support@lexai.com
- **Website**: https://lexai.com
- **Documentation**: https://docs.lexai.com

