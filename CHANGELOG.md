# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/).

---

## [2.5.0] - 2026-03-07

### Added — Backend

- **Multi-provider LLM support** — OpenAI, Anthropic Claude, Groq, Google Gemini alongside existing Ollama. Provider registry with caching and health checks.
- **File upload & RAG** — Upload PDF, DOCX, TXT, MD, CSV. Files are parsed, chunked, embedded into ChromaDB, and queryable via semantic search.
- **Query classification** — Auto-detects focus mode (General, Academic, Code, News, Math, Creative) from the query text.
- **Widget system** — Calculator (safe math eval), unit conversion (temperature, distance, weight), definition detection.
- **Stock widget API** — Real-time stock quotes via Yahoo Finance (`/api/v1/widgets/stock`).
- **Image search API** — Search images via SearXNG (`/api/v1/search/images`).
- **Video search API** — Search videos via SearXNG (`/api/v1/search/videos`).
- **Social/discussion search API** — Reddit, StackOverflow results (`/api/v1/search/social`).
- **Discover feed API** — Trending articles by category (`/api/v1/discover`).
- **Export API** — Export answers as Markdown or plain text (`/api/v1/export/`).
- **Config management API** — Read and update settings at runtime (`/api/v1/config/`).
- **Provider management API** — List, set active, health-check LLM providers (`/api/v1/providers`).
- **Streaming response blocks** — 7 new SSE event types for rich frontend rendering.
- **Rate limiting** — Sliding-window per-IP rate limiter (60 req/min default).
- **Security headers** — OWASP-compliant middleware (CSP, HSTS, X-Content-Type, X-Frame).
- **File upload security** — Magic bytes verification, filename sanitization, extension allowlist, 20MB limit.
- **Session token security** — SHA-256 hashed tokens with TTL, rotation, invalidation.
- **Accurate token counting** — tiktoken integration replacing `len(text)//4` approximation.

### Added — Frontend

- **Component architecture refactor** — Monolithic 1499-line demo.tsx decomposed into 19 focused components.
- **Discover page** — Category tabs (Trending, Science, Technology, Culture), article cards, "Research this" button.
- **Library page** — Search, filter, sort, bulk delete, and export past conversations.
- **Settings modal** — 4-tab settings (General, Intelligence, Appearance, Data), multi-provider selector.
- **ThinkBox** — Chain-of-thought display, parses `<think>` tags, collapsible.
- **Image search panel** — Grid layout with lightbox.
- **Video search panel** — Thumbnails with duration badges.
- **Weather widget** — Open-Meteo API, geolocation, 5-day forecast.
- **Stock widget** — Ticker search, price display, day stats.
- **Calculator/conversion/definition widget** — WidgetCard component.
- **File upload UI** — Paperclip button, file preview chips, drag support.
- **Text-to-speech** — Web Speech API on any response.
- **Enhanced code blocks** — Language label and copy button.
- **Message regenerate** — Re-run any response.
- **Enhanced citations** — Sidebar source cards with favicons + inline citation chips.
- **Mobile responsiveness** — Overlay sidebar, hamburger menu, responsive padding.
- **Enhanced landing page** — Quick suggestion buttons + weather widget.
- **Toast notifications** — Success/error/warning/info toasts with auto-dismiss.

### Added — Infrastructure

- **GitHub Actions CI/CD** — Backend lint/test/security scan, frontend type-check/build, Docker build validation.
- **Production Docker Compose** — nginx reverse proxy, healthchecks, resource limits, API key enforcement.
- **nginx config** — Rate limiting, security headers, SSE proxy support.
- **SearXNG engine config** — 18 engines: Google, Bing, Brave, DuckDuckGo, Google Scholar, arXiv, Semantic Scholar, PubMed, Google News, Bing News, Google Images, Bing Images, Google Videos, Bing Videos, YouTube, Reddit, StackOverflow, GitHub, Wikipedia.

### Changed

- `docker-compose.yml` — Removed obsolete `version` attribute.
- LLM provider `count_tokens()` — Now uses tiktoken instead of `len//4`.
- `SmartChunker._estimate_tokens()` — Now uses tiktoken.
- `ContentChunk.token_count` — Now uses tiktoken.

---

## [2.0.0] - 2026-02-01

### Added
- Initial public release
- Multi-agent research orchestration (LangGraph)
- Three research modes (Quick, Balanced, Deep)
- Six research profiles (General, Academic, Technical, News, Medical, Legal)
- Real-time streaming with Server-Sent Events (SSE)
- Web search via SearXNG (privacy-focused)
- Web crawling with Playwright
- Claim verification and reliability scoring
- Inline citation system
- Session history with local storage
- React 19 frontend with three themes (Light, Dark, Diogenes)
- FastAPI backend with Swagger docs
- SQLite caching and session storage
- Comprehensive configuration system (YAML + env vars)
- Docker Compose support

---

## Roadmap

### v3.0
- [ ] User authentication and accounts
- [ ] Real-time collaboration
- [ ] Plugin system for extensions
- [ ] Multi-language support
- [ ] Knowledge graph visualization
- [ ] Mobile apps
