<div align="center">

<img src="docs/images/logo.png" alt="Diogenes Logo" width="200"/>

# 🔍 Diogenes

### AI-Powered Research Assistant with Multi-Agent Architecture

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://reactjs.org/)

[Features](#-features) • [Demo](#-demo) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 📖 Overview

**Diogenes** is an open-source AI research assistant that searches, crawls, and synthesizes information from the web to provide comprehensive, cited answers to complex queries. Named after the ancient Greek philosopher who searched for truth, Diogenes uses a multi-agent architecture to deliver reliable, fact-checked research.

### Why Diogenes?

- 🎯 **Multi-Agent Architecture**: Specialized agents for search, crawling, synthesis, and verification
- 🔍 **Privacy-Focused Search**: Uses SearXNG for privacy-respecting multi-engine search
- 📚 **Smart Web Crawling**: Extracts clean content from web pages using Playwright
- ✅ **Claim Verification**: Automatic fact-checking with reliability scoring
- 📝 **Cited Answers**: Every claim is backed by sources with inline citations
- ⚡ **Real-Time Streaming**: Watch research progress with Server-Sent Events
- 🎨 **Beautiful UI**: Modern, responsive frontend built with React and Tailwind CSS
- 🔧 **Fully Customizable**: Six research profiles and three depth modes

---

## ✨ Features

### Research Capabilities

- **Three Research Modes**
  - 🚀 **Quick**: Fast answers in ~30 seconds (3-5 sources)
  - ⚖️ **Balanced**: Standard research in ~1 minute (5-8 sources)
  - 🔬 **Deep**: Comprehensive analysis in ~3 minutes (10-15 sources)

- **Six Research Profiles**
  - 🌍 **General**: Broad, accessible answers
  - 🎓 **Academic**: Scholarly with citations and formal language
  - 💻 **Technical**: Implementation details and specifications
  - 📰 **News**: Recent events and multiple perspectives
  - ⚕️ **Medical**: Clinical accuracy with disclaimers
  - ⚖️ **Legal**: Statutes, precedents, and legal terminology

### Technical Features

- **Backend (Python + FastAPI)**
  - Multi-agent orchestration with LangGraph
  - Streaming API with Server-Sent Events (SSE)
  - Configurable LLM backend (Ollama by default)
  - Intelligent web crawling with Playwright
  - SQLite-based caching and session storage
  - Comprehensive error handling and logging

- **Frontend (React + TypeScript)**
  - Real-time streaming research updates
  - Session history with local storage
  - Inline citation references
  - Source panel with quality indicators
  - Three beautiful themes (Light, Dark, Diogenes)
  - Responsive design for mobile and desktop

---

## 🎬 Demo

> **Note**: Screenshots and demo GIF coming soon!

```
User Query: "What is quantum entanglement?"

Diogenes:
┌─────────────────────────────────────────────────────┐
│ Searching 5 sources...                              │
│ Crawling quantum physics papers...                  │
│ Extracting key facts...                             │
│ Synthesizing answer...                              │
│ Verifying claims...                                 │
└─────────────────────────────────────────────────────┘

Quantum entanglement is a phenomenon in quantum mechanics where
two or more particles become correlated in such a way that the
state of one particle instantaneously influences the state of
the other(s), regardless of distance [1][2]...

Sources:
[1] Stanford Encyclopedia of Philosophy
[2] Nature Physics Journal
[3] MIT OpenCourseWare
...
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)
- **Docker** (for SearXNG search engine - **REQUIRED**)
- **Ollama** (recommended for local LLMs) or access to cloud LLM API

**⚠️ Important:** SearXNG must be running before starting the backend!

### Installation

#### Option 1: Automated Setup (Windows PowerShell)

```powershell
# Clone the repository
git clone https://github.com/yourusername/diogenes.git
cd diogenes

# IMPORTANT: Start SearXNG first (required!)
docker-compose up -d --build searxng

# Wait a few seconds for SearXNG to start
Start-Sleep -Seconds 5

# Run the automated setup script
.\start-diogenes.ps1
```

**Note:** The script will check for SearXNG and refuse to start without it!

This script will:
1. Verify SearXNG is running (required!)
2. Install all dependencies
3. Start backend and frontend services
4. Open your browser to `http://localhost:5173`

#### Option 2: Manual Setup

**1. Clone and Setup Backend**

```bash
# Clone repository
git clone https://github.com/yourusername/diogenes.git
cd diogenes

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp .env.example .env  # Edit with your settings
```

**2. Start SearXNG (Search Engine) - REQUIRED!**

```bash
# Using Docker Compose (recommended)
docker-compose up -d --build searxng

# Verify it's running
curl http://localhost:8080/

# SearXNG will be available at http://localhost:8080
```

**⚠️ The backend will NOT work without SearXNG running!**

**Note**: First build takes 2-3 minutes. Subsequent starts are instant.

**3. Start Ollama (LLM Backend)**

```bash
# Install Ollama from https://ollama.ai
# Pull required models
ollama pull llama3.1:8b
ollama pull qwen2.5:3b
```

**4. Start Backend API**

```bash
# From project root
python run_api.py

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

**5. Start Frontend**

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at http://localhost:5173
```

**6. Open Your Browser**

Navigate to `http://localhost:5173` and start researching!

---

## 📚 Documentation

### Configuration

Diogenes uses a hierarchical configuration system with the following precedence:

1. **Environment variables** (`DIOGENES_*`)
2. **Environment-specific YAML** (`config/{environment}.yaml`)
3. **Default YAML** (`config/default.yaml`)
4. **Code defaults**

**Key Environment Variables:**

```bash
# Environment
export DIOGENES_ENV=development  # or production

# Search (SearXNG)
export DIOGENES_SEARCH_BASE_URL=http://localhost:8080

# LLM (Ollama)
export DIOGENES_LLM_BASE_URL=http://localhost:11434
export DIOGENES_LLM_MODEL_SYNTHESIZER=llama3.1:8b

# API
export DIOGENES_API_PORT=8000
export DIOGENES_API_CORS_ORIGINS="http://localhost:5173"
```

See `.env.example` for a complete list of configuration options.

### Architecture

```
┌──────────────┐         ┌───────────────┐         ┌──────────────┐
│   Frontend   │         │   Backend     │         │   SearXNG    │
│ React + Vite │ ◄─SSE──►│   FastAPI     │ ◄──────►│   (Docker)   │
│  Port 5173   │         │   Port 8000   │         │   Port 8080  │
└──────────────┘         └───────────────┘         └──────────────┘
                                 │
                                 ├──► Ollama (LLM)
                                 │    Port 11434
                                 │
                                 ▼
                        ┌────────────────┐
                        │ Multi-Agent    │
                        │ Orchestrator   │
                        └────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
          Search Agent    Crawl Agent    Synthesis Agent
                                         Verification Agent
```

**Backend Architecture:**
- **FastAPI** for REST API and SSE streaming
- **LangGraph** for multi-agent orchestration
- **Playwright** for web crawling
- **Ollama** for local LLM inference
- **SearXNG** for privacy-focused search
- **SQLite** for caching and sessions

**Frontend Architecture:**
- **React 19** with TypeScript
- **Vite** for development and building
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **React Markdown** for answer rendering

### API Endpoints

#### Research API v1

**POST `/api/v1/research/`** - Blocking research query
```json
{
  "query": "What is quantum computing?",
  "mode": "balanced"
}
```

**POST `/api/v1/research/stream`** - Streaming research with SSE
```json
{
  "query": "Explain AI safety",
  "mode": "deep",
  "profile": "academic"
}
```

**GET `/api/v1/health/`** - Health check

See full API documentation at `http://localhost:8000/docs` after starting the backend.

---

## � Documentation

Comprehensive documentation is available in the [docs/](docs/) directory:

### 📖 For Users
- **[Startup Guide](docs/guides/STARTUP_GUIDE.md)** - Detailed setup and installation
- **[Research Modes](docs/guides/MODES.md)** - Understanding research modes and profiles
- **[API Specification](docs/guides/API_SPECIFICATION.md)** - Complete API documentation

### 🏗️ For Developers
- **[Architecture Design](docs/architecture/architecture_design.md)** - System architecture overview
- **[System Design](docs/architecture/SYSTEM_DESIGN.md)** - Detailed component design
- **[Data Flow Diagrams](docs/architecture/DATA_FLOW_DIAGRAMS.md)** - Visual architecture
- **[Backend Documentation](docs/backend/)** - Backend implementation details

### 🚀 For Deployment
- **[Deployment Guide](docs/deployment/DEPLOYMENT.md)** - Production deployment instructions

### 🐛 Troubleshooting
- **[Windows Compatibility](docs/troubleshooting/WINDOWS_COMPATIBILITY.md)** - Windows-specific fixes
- **[Windows Crawling Fix](docs/troubleshooting/WINDOWS_CRAWLING_FIX.md)** - Playwright on Windows

📖 **[Browse All Documentation →](docs/README.md)**

---

## �🛠️ Development

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# Integration tests
python scripts/test_integration.py

# Frontend tests (if implemented)
cd frontend && npm test
```

### Code Quality

```bash
# Python formatting
black src/ tests/

# Python linting
flake8 src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
diogenes/
├── src/                    # Backend source code
│   ├── api/               # FastAPI routes and schemas
│   ├── core/              # Core business logic
│   │   ├── agents/        # Multi-agent orchestration
│   │   ├── citation/      # Citation extraction
│   │   └── research/      # Research pipeline
│   ├── services/          # External service integrations
│   │   ├── crawl/         # Web crawling
│   │   ├── llm/           # LLM service
│   │   └── search/        # Search service
│   ├── storage/           # Data persistence
│   └── utils/             # Utilities
├── frontend/              # React frontend
│   ├── components/        # React components
│   ├── lib/               # Utilities and services
│   └── public/            # Static assets
├── config/                # Configuration files
├── docs/                  # Documentation (organized by category)
│   ├── architecture/      # System design documents
│   ├── guides/            # User guides
│   ├── backend/           # Backend documentation
│   ├── deployment/        # Deployment guides
│   ├── troubleshooting/   # Problem solving
│   └── planning/          # Project planning
├── tests/                 # Test suite
└── scripts/               # Utility scripts
```



---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Areas for Contribution

- 🐛 **Bug fixes**: Check [Issues](https://github.com/yourusername/diogenes/issues)
- ✨ **New features**: Research profiles, export formats, analytics
- 📚 **Documentation**: Tutorials, guides, API examples
- 🧪 **Testing**: Increase coverage, add integration tests
- 🎨 **UI/UX**: Design improvements, accessibility
- 🌍 **Internationalization**: Translations, multi-language support

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### What this means:
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ℹ️ License and copyright notice required

---

## 🙏 Acknowledgments

### Built With

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - UI library
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [SearXNG](https://github.com/searxng/searxng) - Privacy-respecting metasearch engine
- [Playwright](https://playwright.dev/) - Web crawling and automation
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework

### Inspiration

Named after **Diogenes of Sinope**, the ancient Greek philosopher who wandered with a lamp in daylight, searching for an honest person - symbolizing the quest for truth and genuine knowledge.

---

## 🌟 Star History

If you find Diogenes useful, please consider giving it a star ⭐ on GitHub!

---

## 📞 Support

- **Documentation**: [Full Documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/diogenes/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/diogenes/discussions)

---

## 🗺️ Roadmap

### v2.1 (Next Release)
- [ ] Export research to PDF/Markdown
- [ ] User authentication and accounts
- [ ] Backend session persistence
- [ ] Advanced analytics dashboard

### v2.2
- [ ] Real-time collaboration
- [ ] Custom research profiles
- [ ] Plugin system for extensions
- [ ] Multi-language support

### v3.0
- [ ] Knowledge graph integration
- [ ] Long-term memory and learning
- [ ] Advanced visualization tools
- [ ] Mobile apps (iOS/Android)

---

<div align="center">

Made with ❤️ by the open-source community

**[⬆ Back to Top](#-diogenes)**

</div>
