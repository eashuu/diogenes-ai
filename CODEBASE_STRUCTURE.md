# 📁 Diogenes Codebase Structure

This document provides a comprehensive overview of the Diogenes codebase organization.

## 🎯 Root Directory

```
diogenes/
├── README.md                    # Project overview and quick start
├── LICENSE                      # MIT License
├── CONTRIBUTING.md              # Contribution guidelines
├── CODE_OF_CONDUCT.md          # Code of conduct
├── SECURITY.md                  # Security policy
├── CHANGELOG.md                 # Version history
│
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies
├── pytest.ini                   # Pytest configuration
├── .gitignore                   # Git ignore rules
├── .env.example                 # Environment variable template
│
├── main.py                      # Main application entry point
├── run_api.py                   # API server launcher
├── gen.py                       # Utility script
├── start-diogenes.ps1          # PowerShell startup script (checks SearXNG!)
├── check-services.ps1          # Service health check script
├── docker-compose.yml          # Docker orchestration (SearXNG + Ollama)
│
└── [directories below]
```

## 📂 Directory Structure

### `/src` - Backend Source Code

The main Python backend implementation using FastAPI.

```
src/
├── __init__.py
├── config.py                    # Configuration management
│
├── api/                         # FastAPI application
│   ├── __init__.py
│   ├── app.py                   # FastAPI app initialization
│   ├── metrics.py               # Prometheus metrics
│   ├── routes/                  # API route handlers
│   └── schemas/                 # Pydantic models
│
├── core/                        # Core business logic
│   ├── agents/                  # Multi-agent orchestration
│   ├── citation/                # Citation extraction
│   └── research/                # Research pipeline
│
├── services/                    # External integrations
│   ├── crawl/                   # Web crawling (Playwright)
│   ├── llm/                     # LLM service (Ollama)
│   └── search/                  # Search service (SearXNG)
│
├── storage/                     # Data persistence
│   ├── cache/                   # Caching layer
│   └── session/                 # Session management
│
├── tools/                       # Agent tools
├── processing/                  # Data processing utilities
└── utils/                       # Helper utilities
```

### `/frontend` - React Frontend

Modern React 19 application with TypeScript.

```
frontend/
├── package.json                 # NPM dependencies
├── tsconfig.json                # TypeScript configuration
├── vite.config.ts               # Vite build configuration
├── index.html                   # HTML entry point
│
├── index.tsx                    # React entry point
├── App.tsx                      # Main App component
├── demo.tsx                     # Demo/example component
│
├── components/                  # React components
│   └── ui/                      # UI component library
│
└── lib/                         # Frontend libraries
    ├── api-service.ts           # API client
    ├── api-types.ts             # TypeScript types
    ├── theme-provider.tsx       # Theme management
    └── utils.ts                 # Utility functions
```

### `/docs` - Documentation

Organized documentation by category (see [docs/README.md](docs/README.md)).

```
docs/
├── README.md                    # Documentation index
├── images/                      # Documentation images
│   └── logo.png                 # Project logo
│
├── architecture/                # System architecture
│   ├── architecture_design.md
│   ├── SYSTEM_DESIGN.md
│   └── DATA_FLOW_DIAGRAMS.md
│
├── guides/                      # User guides
│   ├── STARTUP_GUIDE.md
│   ├── STARTUP_CHECKLIST.md     # Quick service verification
│   ├── MODES.md
│   └── API_SPECIFICATION.md
│
├── backend/                     # Backend development
│   ├── BACKEND_COMPLETE.md
│   ├── BACKEND_DEEP_ANALYSIS.md
│   ├── FRONTEND_BACKEND_INTEGRATION.md
│   ├── INTEGRATION_SUMMARY.md
│   └── TODO_BACKEND_REMEDIATION.md
│
├── deployment/                  # Deployment guides
│   ├── DEPLOYMENT.md
│   ├── GITHUB_SETUP.md
│   ├── OPENSOURCE_DELIVERY.md
│   └── OPENSOURCE_READY.md
│
├── troubleshooting/            # Problem solving
│   ├── DIOGENES_ERROR_ANALYSIS_REPORT.md
│   ├── WINDOWS_COMPATIBILITY.md
│   └── WINDOWS_CRAWLING_FIX.md
│
└── planning/                   # Project planning
    └── product_requirements_document.md
```

### `/config` - Configuration Files

Environment-specific YAML configurations.

```
config/
├── default.yaml                 # Default configuration
├── development.yaml             # Development overrides
└── production.yaml              # Production overrides
```

### `/tests` - Test Suite

Comprehensive test coverage using pytest.

```
tests/
├── test_comprehensive.py        # Full system tests
├── test_integration.py          # Integration tests
├── test_ux_features.py          # UX feature tests
├── test_v2_backend.py           # Backend unit tests
└── test_v2_live.py              # Live API tests
```

### `/scripts` - Utility Scripts

Helper scripts for testing and verification.

```
scripts/
├── smoke_api_test.py           # Quick API validation
├── test_integration.py         # Integration test runner
├── test_searx.py               # SearXNG connection test
└── verify_api.py               # API verification
```

### `/data` - Data Storage

Runtime data and caches (gitignored).

```
data/
└── chromadb/                   # Vector database storage
```

### `/searxng` - SearXNG Configuration

Custom SearXNG search engine settings.

```
searxng/
├── settings.yml                # SearXNG configuration
├── Dockerfile                  # Custom Docker image build
├── .dockerignore              # Build context optimization
└── README.md                   # SearXNG setup guide
```

## 🚫 Ignored Directories

These directories are in `.gitignore` and not tracked:

- `__pycache__/` - Python bytecode
- `.pytest_cache/` - Pytest cache
- `data/` - Runtime data
- `frontend/node_modules/` - NPM packages
- `frontend/dist/` - Build output
- `.venv/`, `venv/` - Virtual environments
- `.vscode/`, `.idea/` - IDE settings
- `_bmad/`, `_bmad-output/` - Internal tooling

## 📝 Configuration Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python production dependencies |
| `requirements-dev.txt` | Python development dependencies |
| `pytest.ini` | Pytest test configuration |
| `.gitignore` | Git ignore patterns |
| `.env.example` | Environment variable template |(SearXNG + Ollama) |
| `start-diogenes.ps1` | Automated startup script with SearXNG check |
| `check-services.ps1` | Service health check utility 
| `docker-compose.yml` | Docker service orchestration |
| `tsconfig.json` | TypeScript compiler options |
| `vite.config.ts` | Vite build configuration |
| `package.json` | NPM dependencies and scripts |

## 🔍 Finding Things

### Looking for...

**API Routes?**
→ `src/api/routes/`

**Agent Logic?**
→ `src/core/agents/`

**UI Components?**
→ `frontend/components/`

**Configuration?**
→ `config/` directory + `.env` file

**Tests?**
→ `tests/` directory

**Documentation?**
→ `docs/` directory (see [docs/README.md](docs/README.md))

**Scripts?**
→ `scripts/` directory

**Build Output?**
→ `frontend/dist/` (not in Git)

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Diogenes                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Frontend (React)          Backend (FastAPI)            │
│  ├── components/           ├── api/                     │
│  ├── lib/                  ├── core/                    │
│  └── services/             │   ├── agents/              │
│                            │   ├── research/            │
│                            │   └── citation/            │
│                            ├── services/                │
│                            │   ├── llm/                 │
│                            │   ├── search/              │
│                            │   └── crawl/               │
│                            └── storage/                 │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  External Services                                       │
│  ├── SearXNG (Search)                                   │
│  ├── Ollama (LLM)                                       │
│  └── Playwright (Crawling)                              │
└─────────────────────────────────────────────────────────┘
```� Key Concepts

### Important: SearXNG is Required!

**SearXNG must be running before starting the backend.** It's not optional - the backend will fail without it.

```powershell
# Start SearXNG first (builds custom image with your settings.yml)
docker-compose up -d --build searxng

# Verify it's running
curl http://localhost:8080/

# Check all services
.\check-services.ps1
```

**Custom Build:** The Dockerfile in `searxng/` builds a custom image that includes your `settings.yml` configuration. This means your settings are baked into the image.

See [docs/guides/STARTUP_CHECKLIST.md](docs/guides/STARTUP_CHECKLIST.md) for details.

## 📚 Key Concepts

### Backend Organization

- **API Layer** (`src/api/`) - HTTP endpoints and request/response handling
- **Core Layer** (`src/core/`) - Business logic and orchestration
- **Services Layer** (`src/services/`) - External service integrations
- **Storage Layer** (`src/storage/`) - Data persistence

### Frontend Organization

- **Components** (`frontend/components/`) - Reusable UI components
- **Libraries** (`frontend/lib/`) - Utilities and service clients
- **Pages** - App.tsx serves as the main page

### Documentation Organization

- **User-Facing** - Guides for end users
- **Developer-Facing** - Architecture and implementation docs
- **Operations-Facing** - Deployment and troubleshooting

## 🤝 Contributing

When contributing:

1. **New Features** → Add to appropriate `/src` or `/frontend` directory
2. **Documentation** → Update relevant `/docs` files
3. **Tests** → Add to `/tests` directory
4. **Scripts** → Place in `/scripts` directory
5. **Configuration** → Update `/config` files as needed

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

**Last Updated**: February 2026
