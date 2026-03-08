# Contributing to Diogenes

Thanks for your interest in contributing! This guide will get you set up.

## Quick Steps

1. Fork the repo
2. `git checkout -b feature/my-feature`
3. Make changes
4. Test: `pytest tests/ -v` and `cd frontend && npx tsc --noEmit`
5. Commit: `git commit -m "feat: add my feature"`
6. Push and open a PR

## Development Setup

### Backend

```bash
git clone https://github.com/YOUR_USERNAME/diogenes.git
cd diogenes
python -m venv venv
venv\Scripts\activate             # Windows
# source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start SearXNG
docker compose up -d searxng

# Run backend
python run_api.py

# Run tests
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Dev server on http://localhost:5173
npx tsc --noEmit     # Type check
npm run build        # Production build
```

### Docker (full stack)

```bash
docker compose up -d
```

## What to Work On

- **Bugs**: Check [Issues](https://github.com/yourusername/diogenes/issues) labeled `bug`
- **Good first issues**: Look for `good-first-issue` label
- **Features**: Discuss in an issue first before starting large features

## Coding Standards

### Python

- Follow PEP 8 (100 char line limit)
- Use type hints on function signatures
- Use Google-style docstrings for public functions
- Format with `black src/ tests/`
- Sort imports with `isort src/ tests/`
- Lint with `ruff check src/`

### TypeScript

- Strict TypeScript — no `any` unless unavoidable
- Define interfaces for data structures
- Functional components with hooks
- Tailwind CSS for styling (no custom CSS unless necessary)

### Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add stock widget
fix: handle empty search results
docs: update API specification
refactor: simplify chunker logic
test: add widget API tests
```

## Pull Request Process

1. Your PR description should explain **what** changed and **why**
2. Link the related issue if one exists
3. Make sure CI passes (lint, type check, tests, build)
4. Keep PRs focused — one feature or fix per PR
5. Update docs if you changed APIs or added features

## Project Structure

See [NAVIGATION.md](NAVIGATION.md) for a complete file guide.

Key directories:

| Directory | What's there |
|---|---|
| `src/api/routes/` | FastAPI endpoints |
| `src/core/` | Business logic, agents, widgets |
| `src/services/llm/` | LLM providers (OpenAI, Anthropic, Groq, Gemini, Ollama) |
| `src/services/upload/` | File upload + RAG pipeline |
| `frontend/components/` | 19 React components |
| `frontend/lib/` | Types, API client, theme, utilities |
| `config/` | YAML configuration |
| `tests/` | pytest test suite |

## Testing

### Backend

```bash
pytest tests/ -v                    # All tests
pytest tests/test_comprehensive.py  # Core functionality
pytest tests/test_ux_features.py    # UX feature tests
pytest tests/test_v2_backend.py     # V2 backend tests
```

### Frontend

```bash
cd frontend
npx tsc --noEmit    # Type checking
npm run build       # Full build verification
```

## Reporting Bugs

Include:
- Steps to reproduce
- Expected vs actual behavior
- OS, Python version, Node version
- Error logs or screenshots

## Security Issues

Do **not** open a public issue. See [SECURITY.md](SECURITY.md) for responsible disclosure.

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Examples:**
```
feat(api): add streaming endpoint for research

Implements Server-Sent Events (SSE) streaming for real-time
research progress updates.

Closes #123
```

```
fix(frontend): resolve citation rendering bug

Citations were not properly linking to sources in deep mode.
Fixed by updating the citation parsing logic.

Fixes #456
```

## Questions?

Feel free to ask questions by:
- Opening a [Discussion](https://github.com/yourusername/diogenes/discussions)
- Reaching out on our Discord (link coming soon)
- Commenting on relevant issues

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project website (coming soon)

Thank you for contributing to Diogenes! 🔍✨
