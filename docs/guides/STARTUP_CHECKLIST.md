# ✅ Diogenes Startup Checklist

Use this checklist to ensure all required services are running before using Diogenes.

## Required Services Checklist

### ☑️ 1. SearXNG (Search Engine) - **MUST BE RUNNING**

```powershell
# Start SearXNG (first build takes 2-3 minutes)
docker-compose up -d --build searxng

# Verify (should return HTML page)
curl http://localhost:8080/
```

**Status:** ⬜ Not running  ✅ Running on port 8080

**Critical:** Backend will fail without SearXNG!

**Note:** The `--build` flag ensures your custom settings.yml is used.

---

### ☑️ 2. Ollama (LLM) - **Recommended**

```powershell
# Start Ollama
ollama serve

# Pull required models
ollama pull qwen2.5:3b
ollama pull llama3.1:8b

# Verify
curl http://localhost:11434/
```

**Status:** ⬜ Not running  ✅ Running on port 11434

---

### ☑️ 3. Backend API

```powershell
# Start backend
python run_api.py

# Verify
curl http://localhost:8000/health/
```

**Status:** ⬜ Not running  ✅ Running on port 8000

---

### ☑️ 4. Frontend

```powershell
# Start frontend
cd frontend
npm run dev

# Browser opens automatically or visit:
# http://localhost:3000
```

**Status:** ⬜ Not running  ✅ Running on port 3000

---

## Quick Verification Commands

```powershell
# Check all services at once
Write-Host "Checking services..." -ForegroundColor Cyan

# SearXNG (REQUIRED)
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/" -UseBasicParsing -TimeoutSec 2
    Write-Host "✅ SearXNG: Running" -ForegroundColor Green
} catch {
    Write-Host "❌ SearXNG: NOT RUNNING (REQUIRED!)" -ForegroundColor Red
}

# Ollama
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/" -UseBasicParsing -TimeoutSec 2
    Write-Host "✅ Ollama: Running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama: Not running (recommended)" -ForegroundColor Yellow
}

# Backend API
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health/" -UseBasicParsing -TimeoutSec 2
    Write-Host "✅ Backend API: Running" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend API: Not running" -ForegroundColor Red
}

# Frontend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/" -UseBasicParsing -TimeoutSec 2
    Write-Host "✅ Frontend: Running" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend: Not running" -ForegroundColor Red
}
```

Save this as `check-services.ps1` and run it anytime!

---

## Common Issues

### ❌ Backend fails with "Search service unavailable"

**Problem:** SearXNG is not running

**Solution:**
```powershell
docker-compose up -d --build searxng
# Wait 5 seconds for startup (first build takes longer)
Start-Sleep -Seconds 5
# Verify
curl http://localhost:8080/
```

**Tip:** First time running? The Docker build takes 2-3 minutes. Be patient!

### ❌ "Cannot connect to LLM"

**Problem:** Ollama is not running or models not downloaded

**Solution:**
```powershell
# Start Ollama
ollama serve

# In another terminal, pull models
ollama pull qwen2.5:3b
ollama pull llama3.1:8b
```

### ❌ Frontend can't connect to backend

**Problem:** Backend not running or wrong URL

**Solution:**
1. Check backend is running: `curl http://localhost:8000/health/`
2. Check frontend `.env.local` has: `VITE_API_URL=http://localhost:8000/api`

---

## Startup Order (Important!)

**Correct order:**

1. **SearXNG** (via docker-compose) ← START FIRST!
2. **Ollama** (if using local LLM)
3. **Backend API** (depends on SearXNG + Ollama)
4. **Frontend** (depends on Backend)

**Wrong order = errors!**

---

## Docker Compose All-in-One

# First time: builds SearXNG image (2-3 minutes)
docker-compose up -d --build

# Check they're running
docker-compose ps

# View logs
docker-compose logs -f searxng
```

Then start backend and frontend manually.

### Rebuilding After Config Changes

```powershell
# After modifying searxng/settings.yml
docker-compose up -d --build searxng
```

Then start backend and frontend manually.

---

## Need Help?

- 📖 See [STARTUP_GUIDE.md](STARTUP_GUIDE.md) for detailed instructions
- 🐛 See [../troubleshooting/](../troubleshooting/) for error solutions
- 💬 Open an issue on GitHub

---

**Pro Tip:** Create a workspace with 4 terminal windows, one for each service!
