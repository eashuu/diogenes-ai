# Startup Checklist

Start services in this order:

## 1. SearXNG (Required)

```powershell
docker-compose up -d searxng
curl http://localhost:8080/          # Should return HTML
```

## 2. LLM Provider

**Ollama (local):**
```powershell
ollama serve
ollama pull llama3.1:8b
```

**Or set a cloud provider key in `.env`:** `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, or `GOOGLE_API_KEY`.

## 3. Backend API

```powershell
python run_api.py
curl http://localhost:8000/health/   # Should return JSON
```

## 4. Frontend

```powershell
cd frontend && npm run dev
```

Open http://localhost:3000

## Quick Health Check

```powershell
.\check-services.ps1
```

## Ports

| Service | Port |
|---------|------|
| Frontend | 3000 |
| Backend API | 8000 |
| SearXNG | 8080 |
| Ollama | 11434 |

---

For detailed setup instructions, see [STARTUP_GUIDE.md](STARTUP_GUIDE.md).

**Pro Tip:** Create a workspace with 4 terminal windows, one for each service!
