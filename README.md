# Metastream V2 - Live Streaming Platform

یک پلتفرم استریم زنده حرفه‌ای با FastAPI, Go, React و Docker.

## 🚀 Quick Start

### 1. Build Docker Images
```bash
docker build -t metastream/prep-worker:stable -f Dockerfile.prep .
docker build -t metastream/stream-worker:stable -f Dockerfile.stream .
```

### 2. Setup Environment
```bash
cp env.template.v2 .env
# Edit .env with your configuration
```

### 3. Start Services
```bash
docker compose up -d
```

### 4. Check Logs
```bash
docker compose logs -f
```

---

## 📂 Project Structure

```
metastream/
├── app/                      # FastAPI application
│   ├── core/                # Core settings
│   ├── models/              # Database models
│   ├── routers/             # API routes
│   ├── tasks/               # Celery tasks
│   ├── utils/               # Utilities
│   ├── middleware/          # Middleware
│   ├── templates/           # HTML templates
│   └── static/              # Static files
├── frontend/                # React admin panel
│   └── src/
├── go-service/              # Go microservice
│   └── handlers/
├── migrations/              # Database migrations
├── tests/                   # Test files
└── plan/                    # Planning documents
```

---

## 📚 Documentation

- [Start Here](./plan/START-HERE.md) - راهنمای شروع
- [Overview](./plan/01-OVERVIEW.md) - معماری کلی
- [Database Schema](./plan/02-DATABASE-SCHEMA.md) - Schema دیتابیس
- [Subdomains](./plan/03-SUBDOMAIN-ARCHITECTURE.md) - تنظیمات subdomain
- [Implementation Phases](./plan/04-IMPLEMENTATION-PHASES.md) - مراحل پیاده‌سازی
- [API Documentation](./plan/05-API-DOCUMENTATION.md) - مستندات API
- [Additional Requirements](./plan/07-ADDITIONAL-REQUIREMENTS.md) - جزئیات تکمیلی
- [Build Images Guide](./plan/08-BUILD-IMAGES-GUIDE.md) - Docker images

---

## 🎯 Features

- ✅ OTP Authentication (4-digit)
- ✅ Phone validation
- ✅ Channel-based routing
- ✅ Live streaming
- ✅ Progressive comment display
- ✅ Admin panel (React)
- ✅ User dashboard
- ✅ Comment moderation
- ✅ Excel export
- ✅ Database backup to Telegram
- ✅ SMS multi-provider support
- ✅ API for external uploads

---

## 🏗️ Tech Stack

- **Backend:** FastAPI (Python 3.11)
- **Microservice:** Go (Golang 1.21+)
- **Frontend:** React + Vite
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **Queue:** Celery
- **Video Processing:** FFmpeg
- **Container:** Docker + Docker Compose

---

## 🌐 Domains

- **Main:** 1.metastream.ir
- **Panel:** panel1.metastream.ir
- **API:** api1.metastream.ir
- **Live:** live1.metastream.ir

---

## 🔧 Services

- `web` - FastAPI application
- `go-service` - Comment polling microservice
- `prep_worker` - Video processing worker
- `stream_worker` - Streaming worker
- `beat` - Celery scheduler
- `flower` - Celery monitoring
- `db` - PostgreSQL
- `redis` - Redis cache

---

## 📝 Environment Variables

See `.env` or `env.template.v2` for all configuration options.

---

## 🚀 Development

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f web

# Restart a service
docker compose restart web

# Stop all services
docker compose down
```

---

**Built with ❤️**

