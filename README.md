<div align="center">

<img src="docs/images/logo.png" alt="Diogenes Logo" width="200"/>

# Diogenes

### Open-Source AI Research Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/) [![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/) [![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://reactjs.org/) [![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

*Search the web, crawl pages, and get cited answers — all from a single query.*

[Quick Start](#-quick-start) · [Features](#-features) · [Screenshots](#-screenshots) · [Docs](#-documentation) · [Contributing](#-contributing)

</div>

---

## What is Diogenes?

Diogenes is an AI-powered research assistant. You ask a question, it searches the web, reads the pages, checks the facts, and gives you a cited answer — like having a research team working for you.

**Key highlights:**

- **Multi-provider LLM** — Use OpenAI, Anthropic, Groq, Google Gemini, or local Ollama models
- **Privacy-first search** — SearXNG metasearch engine, no tracking
- **Real-time streaming** — Watch research happen live with Server-Sent Events
- **Rich UI** — Discover feed, image/video search, weather & stock widgets, chat history library
- **File upload & RAG** — Upload PDFs, DOCX, TXT and ask questions about them
- **Docker-ready** — One command to run everything

Named after the Greek philosopher who searched for truth with a lantern.

---

## Screenshots

> Screenshots coming soon — the UI includes a chat view, Discover page, Library, Settings, and mobile-responsive design.

---

## Quick Start

### What you need

| Requirement | Version | Why |
|---|---|---|
| Python | 3.11+ | Backend API |
| Node.js | 20+ | Frontend build |
| Docker | Latest | SearXNG search engine |
| Ollama | Latest | Local LLM (or use cloud providers) |

### Option 1: Docker (easiest)

```bash
git clone https://github.com/yourusername/diogenes.git
cd diogenes
docker compose up -d
```

This starts the API, frontend, and SearXNG. Open `http://localhost:3000`.

### Option 2: Manual setup

```bash
# 1. Clone
git clone https://github.com/yourusername/diogenes.git
cd diogenes

# 2. Start SearXNG (required)
docker compose up -d searxng

# 3. Start Ollama and pull a model
ollama pull llama3.1:8b

# 4. Backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python run_api.py            # Runs on http://localhost:8000

# 5. Frontend (new terminal)
cd frontend
npm install
npm run dev                  # Runs on http://localhost:5173
```

### Option 3: PowerShell script (Windows)

```powershell
docker compose up -d searxng
.\start-diogenes.ps1
```

### Verify everything works

| Service | URL | Check |
|---|---|---|
| Frontend | http://localhost:5173 | Page loads |
| API | http://localhost:8000/docs | Swagger UI shows |
| SearXNG | http://localhost:8080 | Search page loads |
| Ollama | http://localhost:11434 | Returns "Ollama is running" |

---

## Features

### Research

| Feature | Description |
|---|---|
| **3 Modes** | Quick (~30s), Balanced (~1min), Deep (~3min) |
| **6 Profiles** | General, Academic, Technical, News, Medical, Legal |
| **Streaming** | Live progress updates via SSE |
| **Citations** | Every claim linked to its source |
| **Verification** | Automatic fact-checking with reliability scores |
| **Follow-ups** | Ask follow-up questions in the same session |

### Frontend

| Feature | Description |
|---|---|
| **Chat** | Multi-session chat with streaming responses |
| **Discover** | Trending articles across Science, Technology, Culture |
| **Library** | Search, filter, sort, and export past conversations |
| **Settings** | Multi-provider LLM config, theme picker, connection testing |
| **ThinkBox** | See the AI's chain-of-thought reasoning |
| **Images/Videos** | Search results with lightbox and thumbnails |
| **Widgets** | Weather, stock quotes, calculator, unit conversion |
| **File Upload** | Attach PDF, DOCX, TXT, MD, CSV for RAG queries |
| **TTS** | Text-to-speech on any response |
| **Themes** | Light, Dark, and Diogenes (warm amber) |
| **Mobile** | Fully responsive with hamburger sidebar |

### Backend API

| Feature | Description |
|---|---|
| **Multi-provider LLM** | OpenAI, Anthropic, Groq, Gemini, Ollama |
| **File Upload + RAG** | Upload → extract → chunk → embed → query |
| **Query Classification** | Auto-detects focus mode from your question |
| **Widget System** | Calculator, unit conversion, definitions |
| **Stock Widget** | Real-time quotes via Yahoo Finance |
| **Config API** | Read/update settings at runtime |
| **Export** | Export answers as Markdown or plain text |
| **Rate Limiting** | Sliding-window per-IP rate limiter |
| **Security Headers** | OWASP-compliant middleware |
| **Session Tokens** | SHA-256 hashed, TTL-based, rotatable |

### Infrastructure

| Feature | Description |
|---|---|
| **Dockerfiles** | Multi-stage builds for API and frontend |
| **docker-compose.yml** | Dev environment with all services |
| **docker-compose.prod.yml** | Production with nginx, healthchecks, resource limits |
| **GitHub Actions CI** | Lint, test, security scan, Docker build on every push |
| **SearXNG** | 18 engines configured (Google, Bing, Scholar, arXiv, Reddit, YouTube, etc.) |

---

## Architecture

```
┌──────────────┐         ┌───────────────┐         ┌──────────────┐
│   Frontend   │         │    Backend    │         │   SearXNG    │
│ React + Vite │ ◄─SSE──►│   FastAPI     │ ◄──────►│   (Docker)   │
│  Port 5173   │         │   Port 8000   │         │   Port 8080  │
└──────────────┘         └───────┬───────┘         └──────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
               LLM Provider  ChromaDB     SQLite
            (Ollama/OpenAI   (vectors)   (cache/sessions)
             /Anthropic/
             Groq/Gemini)
```

**Backend**: Python 3.11, FastAPI, LangGraph, Playwright, httpx
**Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Framer Motion
**Search**: SearXNG with 18 engines (web, academic, news, images, videos, social)
**Storage**: SQLite (sessions/cache), ChromaDB (vector embeddings), NetworkX (knowledge graph)

### Project Structure

```
diogenes/
├── src/                       # Python backend
│   ├── api/                   # FastAPI app, routes, middleware
│   │   ├── routes/            # research, search, discover, export, config, providers, uploads, widgets
│   │   └── middleware.py      # Rate limiting, security headers
│   ├── core/                  # Business logic
│   │   ├── agents/            # Research orchestrator, researcher, writer, verifier
│   │   ├── classifier.py      # Query classification
│   │   └── widgets.py         # Calculator, unit conversion, definitions
│   ├── services/              # External integrations
│   │   ├── llm/               # Multi-provider LLM (OpenAI, Anthropic, Groq, Gemini, Ollama)
│   │   ├── search/            # SearXNG search service
│   │   ├── crawl/             # Playwright web crawler
│   │   └── upload/            # File upload + RAG pipeline
│   ├── processing/            # Content chunking (tiktoken), extraction
│   └── storage/               # SQLite, ChromaDB, NetworkX
├── frontend/                  # React frontend
│   ├── components/            # 19 React components
│   ├── lib/                   # Types, API service, theme, utilities
│   └── demo.tsx               # Main app orchestrator
├── config/                    # YAML configs (default, dev, prod)
├── searxng/                   # SearXNG settings + Dockerfile
├── nginx/                     # Production nginx config
├── tests/                     # pytest test suite
├── scripts/                   # Utility scripts
├── .github/workflows/         # CI/CD pipelines
├── docker-compose.yml         # Dev environment
├── docker-compose.prod.yml    # Production environment
└── docs/                      # Full documentation
```

---

## API Quick Reference

All endpoints live under `/api/v1/`. Full interactive docs at `/docs` when running.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/research/stream` | Start streaming research |
| `POST` | `/research/` | Blocking research query |
| `GET` | `/research/{id}` | Get session results |
| `GET` | `/search/images?q=...` | Image search |
| `GET` | `/search/videos?q=...` | Video search |
| `GET` | `/search/social?q=...` | Discussion/social search |
| `GET` | `/discover?category=...` | Trending articles |
| `POST` | `/uploads` | Upload a file for RAG |
| `POST` | `/uploads/query` | Query uploaded files |
| `GET` | `/providers` | List LLM providers |
| `POST` | `/providers/active` | Set active provider |
| `GET` | `/widgets/stock?symbol=...` | Stock quote |
| `POST` | `/export/` | Export answer as Markdown/text |
| `GET` | `/config/` | Get current config |
| `POST` | `/config/` | Update config |
| `GET` | `/health/` | Health check |

---

## Configuration

Diogenes uses layered config: **env vars** > **YAML files** > **defaults**.

### Environment variables

```bash
# Core
DIOGENES_ENV=development              # development | production
DIOGENES_SEARCH_BASE_URL=http://localhost:8080
DIOGENES_LLM_BASE_URL=http://localhost:11434

# LLM Providers (set the ones you use)
DIOGENES_PROVIDERS_OPENAI_API_KEY=sk-...
DIOGENES_PROVIDERS_ANTHROPIC_API_KEY=sk-ant-...
DIOGENES_PROVIDERS_GROQ_API_KEY=gsk_...
DIOGENES_PROVIDERS_GEMINI_API_KEY=AI...

# API Security (optional, for production)
DIOGENES_API_REQUIRE_API_KEY=true
DIOGENES_API_API_KEY=your-secret-key
```

### YAML config files

- `config/default.yaml` — Base settings (LLM models, processing, search, API)
- `config/development.yaml` — Dev overrides
- `config/production.yaml` — Prod overrides

---

## Documentation

| Doc | What it covers |
|---|---|
| **[Startup Guide](docs/guides/STARTUP_GUIDE.md)** | Step-by-step setup |
| **[Research Modes](docs/guides/MODES.md)** | Quick / Balanced / Deep + 6 profiles |
| **[API Specification](docs/guides/API_SPECIFICATION.md)** | All endpoints with examples |
| **[Architecture Design](docs/architecture/architecture_design.md)** | System design overview |
| **[Data Flow Diagrams](docs/architecture/DATA_FLOW_DIAGRAMS.md)** | Visual data flows |
| **[Deployment Guide](docs/deployment/DEPLOYMENT.md)** | Docker, production, nginx |
| **[Windows Fixes](docs/troubleshooting/WINDOWS_COMPATIBILITY.md)** | Windows-specific issues |
| **[All Docs](docs/README.md)** | Full documentation index |

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

**Quick version:**

```bash
# Fork → Clone → Branch
git checkout -b feature/my-feature

# Make changes → Test
pytest tests/ -v
cd frontend && npx tsc --noEmit

# Commit (conventional commits)
git commit -m "feat: add my feature"

# Push → Open PR
git push origin feature/my-feature
```

---

## License

MIT — see [LICENSE](LICENSE). Use it however you want.

---

## Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com/), [React](https://reactjs.org/), [LangGraph](https://github.com/langchain-ai/langgraph), [SearXNG](https://github.com/searxng/searxng), [Playwright](https://playwright.dev/), [Ollama](https://ollama.ai/), [Tailwind CSS](https://tailwindcss.com/), [Framer Motion](https://www.framer.com/motion/).

---

<div align="center">

**[Back to top](#diogenes)**

</div>

**[⬆ Back to Top](#-diogenes)**

</div>
