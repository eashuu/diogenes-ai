# Startup & Verification Guide

## Prerequisites

SearXNG is required for web search. Start it first:

```powershell
docker-compose up -d searxng
```

Verify: `curl http://localhost:8080/` should return the SearXNG page.

You also need at least one LLM provider running:
- **Ollama** (local): `ollama serve` then `ollama pull llama3.1:8b`
- **Cloud**: Set the appropriate API key in `.env` (OpenAI, Anthropic, Groq, or Google Gemini)

---

## Quick Start

### 1. Start Backend (Port 8000)

```powershell
python run_api.py
```

Or directly:
```powershell
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

### 2. Start Frontend (Port 3000)

```powershell
cd frontend
npm run dev
```

### 3. Open Browser

http://localhost:3000 — the frontend connects to the backend automatically.

---

## API Endpoints

### Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/research/` | Start research (blocking) |
| POST | `/api/v1/research/stream` | Start research (SSE streaming) |
| GET | `/api/v1/research/sessions` | List recent sessions |
| GET | `/api/v1/research/{session_id}` | Get session results |
| DELETE | `/api/v1/research/{session_id}` | Delete session |
| POST | `/api/v1/research/{session_id}/followup` | Follow-up question |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/search/images` | Image search |
| POST | `/api/v1/search/videos` | Video search |
| POST | `/api/v1/search/social` | Social/discussion search |

### Discover & Library

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/discover` | Trending articles by category |
| POST | `/api/v1/export/{format}` | Export as markdown or text |

### Widgets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/widgets/stock` | Stock quotes |
| POST | `/api/v1/widgets/calculate` | Calculator |

### Config & Providers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/config/` | Get settings |
| PUT | `/api/v1/config/` | Update settings |
| GET | `/api/v1/providers` | List LLM providers |
| PUT | `/api/v1/providers/active` | Set active provider |
| GET | `/api/v1/providers/health` | Provider health check |

### Uploads

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/uploads/` | Upload file for RAG |
| GET | `/api/v1/uploads/` | List uploaded files |
| DELETE | `/api/v1/uploads/{id}` | Delete uploaded file |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Health check |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe |

---

## Environment Configuration

### Backend (.env)

```bash
# API
DIOGENES_API_HOST=127.0.0.1
DIOGENES_API_PORT=8000

# Search
DIOGENES_SEARCH_BASE_URL=http://localhost:8080

# LLM — Ollama (local)
DIOGENES_LLM_BASE_URL=http://localhost:11434
DIOGENES_LLM_MODEL_PLANNER=qwen2.5:3b
DIOGENES_LLM_MODEL_SYNTHESIZER=llama3.1:8b

# LLM — Cloud providers (optional, set any one)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GROQ_API_KEY=gsk_...
# GOOGLE_API_KEY=...
```

### Frontend (.env.local)

```bash
VITE_API_URL=http://localhost:8000/api
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Cannot connect to research backend" | Check backend is running: `curl http://localhost:8000/health/` |
| "Ollama not available" | Run `ollama serve` and pull a model |
| "SearXNG not available" | `docker-compose up -d searxng` |
| CORS error in browser | Check `DIOGENES_API_CORS_ORIGINS` in `.env` |
| Frontend shows blank page | Check `VITE_API_URL` in `frontend/.env.local` |

```powershell
# Build and start SearXNG and Ollama
docker-compose up -d --build

# Then start backend and frontend manually as above
```

### Rebuilding SearXNG after settings changes

```powershell
# After modifying searxng/settings.yml
docker-compose up -d --build searxng
# Then start backend and frontend manually as above
```
