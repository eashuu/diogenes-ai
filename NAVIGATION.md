# 🗺️ Quick Navigation Guide

A quick reference for navigating the Diogenes codebase.

## 🚀 Getting Started

| I want to... | Go to... |
|-------------|----------|
| **Understand the project** | [README.md](README.md) |
| **Set up locally** | [docs/guides/STARTUP_GUIDE.md](docs/guides/STARTUP_GUIDE.md) |
| **Quick service check** | [docs/guides/STARTUP_CHECKLIST.md](docs/guides/STARTUP_CHECKLIST.md) |
| **Understand the structure** | [CODEBASE_STRUCTURE.md](CODEBASE_STRUCTURE.md) |
| **Contribute** | [CONTRIBUTING.md](CONTRIBUTING.md) |

## 🔧 Development

| I want to... | Go to... |
|-------------|----------|
| **Add a new API endpoint** | [src/api/routes/](src/api/routes/) |
| **Modify agent logic** | [src/core/agents/](src/core/agents/) |
| **Change research pipeline** | [src/core/research/](src/core/research/) |
| **Update UI components** | [frontend/components/](frontend/components/) |
| **Modify API client** | [frontend/lib/api-service.ts](frontend/lib/api-service.ts) |
| **Add/modify tests** | [tests/](tests/) |
| **Update configuration** | [config/](config/) + `.env` |

## 📚 Documentation

| I need to... | Go to... |
|-------------|----------|
| **Read user guides** | [docs/guides/](docs/guides/) |
| **Understand architecture** | [docs/architecture/](docs/architecture/) |
| **Learn about backend** | [docs/backend/](docs/backend/) |
| **Deploy the app** | [docs/deployment/](docs/deployment/) |
| **Fix an issue** | [docs/troubleshooting/](docs/troubleshooting/) |
| **Browse all docs** | [docs/README.md](docs/README.md) |

## 🐛 Troubleshooting

| Issue | Documentation |
|-------|--------------|
| **Windows-specific issues** | [docs/troubleshooting/WINDOWS_COMPATIBILITY.md](docs/troubleshooting/WINDOWS_COMPATIBILITY.md) |
| **Crawling problems** | [docs/troubleshooting/WINDOWS_CRAWLING_FIX.md](docs/troubleshooting/WINDOWS_CRAWLING_FIX.md) |
| **General errors** | [docs/troubleshooting/DIOGENES_ERROR_ANALYSIS_REPORT.md](docs/troubleshooting/DIOGENES_ERROR_ANALYSIS_REPORT.md) |

## 🎯 Common Tasks

### Adding a New Feature

1. **Backend**: Add logic in `src/core/` or `src/services/`
2. **API**: Create endpoint in `src/api/routes/`
3. **Frontend**: Update `frontend/components/` and `frontend/lib/`
4. **Tests**: Add tests in `tests/`
5. **Docs**: Update relevant documentation in `docs/`

### Fixing a Bug

1. **Reproduce**: Write a failing test in `tests/`
2. **Locate**: Use `CODEBASE_STRUCTURE.md` to find relevant code
3. **Fix**: Modify code in appropriate `src/` or `frontend/` directory
4. **Verify**: Run tests with `pytest tests/ -v`
5. **Document**: Update troubleshooting docs if needed

### Updating Documentation

1. **User guides** → `docs/guides/`
2. **Architecture** → `docs/architecture/`
3. **Backend details** → `docs/backend/`
4. **Deployment info** → `docs/deployment/`
5. **Troubleshooting** → `docs/troubleshooting/`
6. **Project planning** → `docs/planning/`

Update the [docs/README.md](docs/README.md) index when adding new docs.

## 📁 File Locations

### Configuration

- **Environment variables**: `.env` (create from `.env.example`)
- **YAML configs**: `config/default.yaml`, `config/development.yaml`, `config/production.yaml`
- **Python deps**: `requirements.txt`, `requirements-dev.txt`
- **Frontend deps**: `frontend/package.json`
- **Docker setup**: `docker-compose.yml`

### Entry Points

- **Main app**: `main.py`
- **API server**: `run_api.py`
- **Frontend dev**: `cd frontend && npm run dev`
- **Tests**: `pytest tests/`

### Important Configs

- **API config**: `src/config.py` + `config/*.yaml`
- **Frontend config**: `frontend/vite.config.ts`
- **Test config**: `pytest.ini`
- **Search config**: `searxng/settings.yml`

## 🔍 Search Tips

### Finding Code

```bash
# Search for a term in Python files
grep -r "search_term" src/

# Search in frontend
grep -r "search_term" frontend/

# Search in all docs
grep -r "search_term" docs/
```

### Finding Documentation

```bash
# List all markdown files
find docs/ -name "*.md"

# Search in all documentation
grep -ri "keyword" docs/
```

## 📞 Need Help?

- 📖 Check [docs/README.md](docs/README.md) for comprehensive documentation
- 🐛 Open an issue on GitHub
- 💬 Start a discussion on GitHub Discussions
- 📧 Contact maintainers (see README.md)

---

**Pro Tip**: Bookmark this file for quick reference while developing!

**Last Updated**: February 2026
