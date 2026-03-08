# Deployment Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker (Development)](#docker-development)
- [Docker (Production)](#docker-production)
- [Manual Production Setup](#manual-production-setup)
- [CI/CD Pipeline](#cicd-pipeline)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Backend |
| Node.js | 20+ | Frontend |
| Docker | 20.10+ | Optional — for containerized deployment |
| Docker Compose | v2+ | Included with Docker Desktop |
| Git | Latest | Source control |

**External Services:**
- **SearXNG** — Web search (included in Docker setup)
- **LLM Provider** — At least one of: Ollama (local), OpenAI, Anthropic, Groq, Google Gemini

---

## Local Development

### 1. Clone & Setup Backend

```bash
git clone https://github.com/eashuu/diogenes.git
cd diogenes
python -m venv venv
venv\Scripts\Activate.ps1          # Windows PowerShell
# source venv/bin/activate         # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
DIOGENES_SEARCH_BASE_URL=http://localhost:8080
DIOGENES_LLM_BASE_URL=http://localhost:11434   # Ollama

# Optional cloud providers:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GROQ_API_KEY=gsk_...
# GOOGLE_API_KEY=...
```

### 3. Setup Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Start Everything

**Option A — Automated (Windows):**
```powershell
.\start-diogenes.ps1
```

**Option B — Manual (4 terminals):**

| Terminal | Command | Purpose |
|----------|---------|---------|
| 1 | `docker-compose up -d searxng` | SearXNG search engine |
| 2 | `ollama serve` | Local LLM (if using Ollama) |
| 3 | `python run_api.py` | Backend API |
| 4 | `cd frontend && npm run dev` | Frontend |

### 5. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| SearXNG | http://localhost:8080 |

---

## Docker (Development)

Start all services with one command:

```bash
docker-compose up -d
docker-compose logs -f          # Watch logs
docker-compose down             # Stop all
```

Services started: backend (8000), frontend (3000), SearXNG (8080), Ollama (11434).

---

## Docker (Production)

Uses `docker-compose.prod.yml` with nginx reverse proxy, health checks, resource limits, and security hardening.

### 1. Set API Keys

```bash
cp .env.example .env
# Edit .env — set at least one LLM provider key
```

### 2. Launch

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### What's Included

| Service | Description |
|---------|-------------|
| **nginx** | Reverse proxy — TLS, rate limiting, security headers, SSE support |
| **diogenes-backend** | FastAPI with gunicorn workers |
| **diogenes-frontend** | Built React app served by nginx |
| **searxng** | Search engine with 18 engines configured |

### Production nginx Features

- Rate limiting (10 req/s burst 20)
- Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- SSE proxy support (buffering off, no timeout)
- Gzip compression
- Static asset caching

### Health Checks

```bash
curl http://localhost/health/        # Backend health
curl http://localhost/health/ready   # Readiness probe
```

---

## Manual Production Setup

For deploying without Docker on a Linux server.

### 1. Server Setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3.11 python3.11-venv python3-pip git nginx -y
git clone https://github.com/eashuu/diogenes.git
cd diogenes
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn
```

### 2. Systemd Service

Create `/etc/systemd/system/diogenes.service`:

```ini
[Unit]
Description=Diogenes Backend API
After=network.target

[Service]
User=diogenes
WorkingDirectory=/home/diogenes/diogenes
Environment="PATH=/home/diogenes/diogenes/venv/bin"
ExecStart=/home/diogenes/diogenes/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    src.api.app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now diogenes
```

### 3. Build & Deploy Frontend

```bash
cd frontend && npm run build
sudo cp -r dist/ /var/www/diogenes/
```

### 4. nginx Config

```nginx
upstream diogenes_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        root /var/www/diogenes;
        try_files $uri $uri/ /index.html;
    }

    # Backend API + SSE
    location /api/ {
        proxy_pass http://diogenes_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache off;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

---

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and PR:

| Job | Checks |
|-----|--------|
| **Backend** | Python lint (ruff), pytest, security scan (bandit) |
| **Frontend** | TypeScript type-check, Vite build |
| **Docker** | Compose config validation, image build |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8000 in use | `lsof -i :8000` then `kill -9 <PID>` |
| CORS error in browser | Check `DIOGENES_API_CORS_ORIGINS` in `.env` |
| SearXNG not responding | `docker-compose restart searxng` |
| Ollama connection refused | Run `ollama serve` or check `DIOGENES_LLM_BASE_URL` |
| Frontend can't reach API | Verify `VITE_API_URL` in `frontend/.env.local` |

### Backup

```bash
# SQLite databases
cp data/cache.db backup/
cp data/sessions.db backup/
```
