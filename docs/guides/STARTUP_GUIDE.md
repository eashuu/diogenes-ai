# Diogenes Startup & Verification Guide

## ⚠️ Prerequisites - MUST RUN FIRST!

### Start SearXNG (Required Search Engine)

**SearXNG is a REQUIRED dependency** - the backend will not work without it!

```powershell
# Option 1: Using docker-compose (RECOMMENDED)
cd diogenes
docker-compose up -d --build searxng

# Option 2: Using docker directly
cd searxng
docker build -t diogenes-searxng:latest .
docker run -d -p 8080:8080 --name diogenes-searxng diogenes-searxng:latest
```

**Verify SearXNG is running:**
```powershell
curl http://localhost:8080/
# Should return SearXNG HTML page
```

✅ **SearXNG must be running before starting the backend!**

**Note**: The first build will take a few minutes. Subsequent starts are instant.

---

## Quick Start

### 1. Start Backend API (Port 8000)

```powershell
# From project root
python run_api.py
```

Or with uvicorn directly:
```powershell
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

**Expected output:**
```
INFO: Starting Diogenes API v1.0 (development)
INFO: Prometheus metrics enabled at /health/metrics
INFO: Uvicorn running on http://127.0.0.1:8000
```

### 2. Start Frontend (Port 3000)

```powershell
# From project root  
cd frontend
npm run dev
```

**Expected output:**
```
VITE v5.x.x ready in xxx ms
➜ Local: http://localhost:3000/
```

### 3. Verify Connection

Open browser to `http://localhost:3000` - frontend should connect to backend automatically.

---

## API Endpoint Reference

### Backend (http://localhost:8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/research/` | Start research (blocking) |
| POST | `/api/v1/research/stream` | Start research (streaming SSE) |
| GET | `/api/v1/research/sessions` | List recent sessions |
| GET | `/api/v1/research/{session_id}` | Get session results |
| DELETE | `/api/v1/research/{session_id}` | Delete session |
| POST | `/api/v1/research/{session_id}/followup` | Ask follow-up question |
| POST | `/api/v1/research/{session_id}/transform` | Quick-action transforms |
| GET | `/api/v1/research/{session_id}/tree` | Get conversation tree |
| POST | `/api/v1/research/{session_id}/branch` | Branch conversation |
| GET | `/api/v1/research/profiles` | List research profiles |
| GET | `/api/v1/research/health` | Research service health |
| GET | `/api/v1/settings/` | Get all settings |
| PUT | `/api/v1/settings/llm` | Update LLM settings |
| PUT | `/api/v1/settings/search` | Update search settings |
| PUT | `/api/v1/settings/agent` | Update agent settings |
| GET | `/api/v1/settings/llm/models` | List available models |
| GET | `/api/v1/settings/status` | Service status |
| POST | `/api/v1/settings/test-connection` | Test service connection |
| POST | `/api/v1/settings/reset` | Reset settings |
| GET | `/api/v1/memory/` | List memories |
| POST | `/api/v1/memory/` | Add memory |
| GET | `/api/v1/memory/{id}` | Get memory |
| PUT | `/api/v1/memory/{id}` | Update memory |
| DELETE | `/api/v1/memory/{id}` | Delete memory |
| GET | `/health/` | Health check |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/metrics` | Prometheus metrics |

### Frontend API Service

The frontend uses `DiogenesAPIService` class in `frontend/lib/api-service.ts`:

```typescript
import { apiService } from './lib/api-service';

// Research
const result = await apiService.research({
  query: "What is quantum computing?",
  mode: "balanced"
});

// Streaming
for await (const event of apiService.researchStream({
  query: "Explain AI safety",
  mode: "full"
})) {
  console.log(event.type, event.data);
}

// Settings
const settings = await apiService.getSettings();
await apiService.updateLLMSettings({ temperature: 0.7 });

// Service status
const status = await apiService.getServicesStatus();
```

---

## Environment Configuration

### Backend (.env)

```bash
# API Configuration
DIOGENES_API_HOST=127.0.0.1
DIOGENES_API_PORT=8000
DIOGENES_API_WORKERS=1

# LLM Configuration
DIOGENES_LLM_BASE_URL=http://localhost:11434
DIOGENES_LLM_MODEL_PLANNER=qwen2.5:3b
DIOGENES_LLM_MODEL_SYNTHESIZER=llama3.1:8b

# Search Configuration
DIOGENES_SEARCH_BASE_URL=http://localhost:8080

# Database Paths
DIOGENES_CACHE_DATABASE=data/cache.db
DIOGENES_SESSION_DATABASE=data/sessions.db
DIOGENES_MEMORY_DATABASE=data/memories.db
DIOGENES_CONVERSATION_DATABASE=data/conversations.db
```

### Frontend (.env.local)

```bash
# Backend API URL
VITE_API_URL=http://localhost:8000/api
```

---

## Troubleshooting

### Error: "Cannot connect to research backend"

**Cause:** Backend API not running or wrong URL

**Fix:**
1. Verify backend is running: `curl http://localhost:8000/health/`
2. Check frontend `.env.local` has `VITE_API_URL=http://localhost:8000/api`
3. Check browser console for CORS errors
4. Verify ports: backend=8000, frontend=3000

### Error: "Ollama not available"

**Cause:** Ollama service not running

**Fix:**
```powershell
# Start Ollama
ollama serve

# Pull required models
ollama pull qwen2.5:3b
ollama pull llama3.1:8b
```

### Error: "SearXNG not available"

**Cause:** SearXNG not running (THIS IS REQUIRED!)

**Fix:**
```powershell
# Start SearXNG via docker-compose (recommended)
docker-compose up -d --build searxng

# OR using docker directly
cd searxng
docker build -t diogenes-searxng:latest .
docker run -d -p 8080:8080 --name diogenes-searxng diogenes-searxng:latest

# Verify it's running
curl http://localhost:8080/
```

**First time setup**: The initial build takes 2-3 minutes. Be patient!

### Error: "CORS policy blocked"

**Cause:** Frontend origin not allowed

**Fix:** Backend already allows `http://localhost:3000` in CORS config. If using different port, update `src/api/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Add your port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Verification Script

Run this to verify all endpoints:

```powershell
python scripts/verify_api.py
```

Or manually:

```powershell
# 1. Health check
curl http://localhost:8000/health/

# 2. Test research endpoint
curl -X POST http://localhost:8000/api/v1/research/ `
  -H "Content-Type: application/json" `
  -d '{"query":"test","mode":"quick"}'

# 3. List profiles
curl http://localhost:8000/api/v1/research/profiles

# 4. Get settings
curl http://localhost:8000/api/v1/settings/

# 5. Service status
curl http://localhost:8000/api/v1/settings/status
```

---

## Port Summary

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8000 | http://localhost:8000 |
| Frontend | 3000 | http://localhost:3000 |
| Ollama | 11434 | http://localhost:11434 |
| **SearXNG (REQUIRED)** | **8080** | **http://localhost:8080** |

---

## Development Workflow

```powershell
# Terminal 1: REQUIRE--build searxng
# Verify: curl http://localhost:8080/
# Note: First build takes 2-3 minutes

# Terminal 2: Start Ollama (if using local LLM)
ollama serve
# Pull models: ollama pull qwen2.5:3b && ollama pull llama3.1:8b

# Terminal 3: Start Backend
python run_api.py
# Verify: curl http://localhost:8000/health/

# Terminal 4: Start Frontend
cd frontend
npm run dev
```

✅ **Then open: http://localhost:3000**

### Using docker-compose for all services

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
