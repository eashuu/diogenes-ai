# TODO — Backend Remediation Plan

**Source of Truth:** `BACKEND_DEEP_ANALYSIS.md`  
**Created:** 2026-02-10  
**Status:** In Progress

---

## P0 — Runtime Crashes

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| B1 | SuggestionAgent passes `model`, `temperature`, `max_tokens` as kwargs to `OllamaService.generate()` which only accepts `(prompt, system, config)` → **TypeError** at runtime | `src/core/agents/suggester.py` | 10 min | 🔴 High | ✅ Fixed |
| B2 | `format_sources_for_synthesis()` has broken conditional f-string logic — else branch always executes, producing garbled source context for LLM | `src/core/agent/prompts.py` | 15 min | 🔴 High | ✅ Fixed |
| B3 | `__init__.py` imports all agent modules transitively at load time — any single file error collapses the entire package | `src/core/agents/__init__.py` | 30 min | 🟡 Medium | ✅ Fixed |

---

## P0 / P1 — Security Issues

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| S1 | ~~No authentication~~ → Local access guard: localhost-only binding (`127.0.0.1` default), network exposure warning, optional API key middleware (`X-API-Key` header), `.env.example` updated | `src/api/app.py`, `src/config.py`, `.env.example` | 1 hour | 🔴 Critical | ✅ Fixed (FOSS-local) |
| S2 | SSRF via crawler — user-supplied URLs crawled without validation against private/internal IPs | `src/services/crawl/crawler.py`, `src/services/crawl/simple_crawler.py` | 1 hour | 🔴 Critical | ✅ Fixed |
| S3 | CORS allows all origins with credentials (`allow_origins=["*"]`) | `src/api/app.py` | 30 min | 🔴 High | ✅ Fixed |
| S4 | ~~IP-rate limiting~~ → Resource semaphores: `asyncio.Semaphore(max_concurrent_research)` gates all V1+V2 research endpoints (default 2); crawl batch cap made configurable via `DIOGENES_CRAWL_MAX_URLS_PER_REQUEST` | `src/api/routes/research.py`, `research_v2.py`, `src/config.py`, `src/services/crawl/crawler.py` | 1 hour | 🟡 Medium | ✅ Fixed (FOSS-local) |
| S5 | ~~User auth~~ → Session-scoped memory: extract endpoint requires explicit `store: true` opt-in (dry-run by default), session-based memory filtering, configurable memory context injection (`DIOGENES_AGENT_ENABLE_MEMORY_CONTEXT`) | `src/api/routes/memory.py`, `src/api/schemas/memory.py`, `src/core/agents/memory.py`, `src/storage/memory_store.py`, `src/core/agents/orchestrator.py`, `src/config.py` | 1 hour | 🔴 High | ✅ Fixed (FOSS-local) |
| S6 | Sensitive internal data (paths, model names) exposed in error responses | `src/utils/exceptions.py` | 30 min | 🟡 Medium | ✅ Fixed |
| S7 | No input size limits on crawl URL count — unbounded crawl requests | `src/services/crawl/crawler.py` | 30 min | 🟡 Medium | ✅ Fixed |
| S8 | XML External Entity (XXE) potential in ArXiv XML parsing | `src/services/search/arxiv.py` | 15 min | 🟡 Medium | ✅ Fixed |
| S9 | All HTTP traffic (Ollama, SearXNG) is plaintext — no HTTPS | All HTTP clients | 30 min | 🟢 Low | ✅ Fixed |

---

## P1 — Logic Errors & Silent Failures

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| B4 | `_phase_processing()` in CoordinatorAgent is a stub — does nothing; V2 skips all content processing | `src/core/agents/coordinator.py` | 3 hours | 🔴 High | ✅ Fixed |
| B5 | `_academic_search()` and `_code_search()` mutate `task.inputs["queries"]` in place | `src/core/agents/researcher.py` | 15 min | 🟡 Medium | ✅ Fixed |
| B6 | `_load_documents()` wired to `PDFLoader` — supports local files and URLs, runs clean→chunk→score pipeline | `src/core/agents/researcher.py`, `src/services/crawl/pdf_loader.py` | 1 hour | 🟢 Low | ✅ Fixed |
| B7 | V1 sessions now persisted via SQLiteSessionStore; `_serialize_state()` flattens citation_map; `_phase_to_status()` handles string phases from deserialized JSON; `_build_response()` handles both live and dict citation formats | `src/api/routes/research.py` | 3 hours | 🔴 High | ✅ Fixed |
| B8 | V2 orchestrators cached per mode and shared across concurrent requests — potential state corruption | `src/api/routes/research_v2.py` | 2 hours | 🔴 High | ✅ Fixed |
| B9 | Runtime `_settings_overrides` now propagate via `apply_runtime_overrides()` — same fix as C1 | `src/api/routes/settings.py`, `src/config.py` | 2 hours | 🟡 Medium | ✅ Fixed (via C1) |
| B10 | Conversation tree `create_node` has read-modify-write race on parent's `children` list | `src/storage/conversation.py` | 30 min | 🟡 Medium | ✅ Fixed |
| B11 | `QuickFactExtractor()` created inside loop per crawl result — re-compiles regex patterns each time | `src/core/agent/nodes.py` | 15 min | 🟢 Low | ✅ Fixed |

---

## P1–P2 — Performance Issues

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| Perf-P1 | Embedding cache now stores `np.ndarray(float32)` — ~3.5× memory reduction (215MB → ~60MB for 10K entries) | `src/services/embedding/service.py`, `requirements.txt` | 1 hour | 🟡 Medium | ✅ Fixed |
| Perf-P2 | Cosine similarity now uses `np.dot()` + `np.linalg.norm()` — ~100× faster; also fixed in `knowledge/graph.py` | `src/services/embedding/service.py`, `src/knowledge/graph.py` | 30 min | 🟡 Medium | ✅ Fixed |
| Perf-P3 | Single-worker Uvicorn — all requests queue behind each other | `run_api.py` | 15 min | 🔴 High | ✅ Fixed |
| Perf-P4 | Shared `httpx.AsyncClient` singletons added to `health.py` and `settings.py` — eliminates per-call TCP connection overhead | `src/api/routes/health.py`, `src/api/routes/settings.py` | 1 hour | 🟡 Medium | ✅ Fixed |
| Perf-P5 | Redundant `QuickFactExtractor` + `CitationManager` creation per node call | `src/core/agent/nodes.py` | 15 min | 🟢 Low | ✅ Fixed (extractor fixed via B11; CitationManager per-node is by design) |
| Perf-P6 | Contradiction detection batched into single LLM call with numbered claims — O(1) instead of O(N²); caps at 20 claims; graceful fallback on parse failure | `src/core/agents/verifier.py` | 1 hour | 🟡 Medium | ✅ Fixed |
| Perf-P7 | Artificial 10ms sleep per 50-char chunk in answer streaming — ~800ms added latency | `src/core/agents/orchestrator.py` | 10 min | 🟢 Low | ✅ Fixed |

---

## P1–P2 — Configuration Issues

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| C1 | Runtime overrides now propagate to `get_settings()` via `apply_runtime_overrides()` in config.py; `_apply_overrides()` merges nested sub-configs; reset endpoint clears global cache | `src/config.py`, `src/api/routes/settings.py` | 1 hour | 🔴 High | ✅ Fixed |
| C2 | Startup health check validates Ollama + SearXNG reachability, warns on plaintext HTTP for non-localhost | `src/api/app.py` | 30 min | 🟡 Medium | ✅ Fixed |
| C3 | Startup check lists available Ollama models and warns if required models (planner, extractor, synthesizer, reflector) are missing | `src/api/app.py` | 30 min | 🟡 Medium | ✅ Fixed |
| C4 | Four separate SQLite DB paths hardcoded — not configurable via `.env` | `src/storage/sqlite.py`, `src/storage/memory_store.py`, `src/storage/conversation.py` | 30 min | 🟡 Medium | ✅ Fixed |

---

## P2 — Architecture: Sync Processing Blocking Event Loop

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| A5/I5 | Sync processing (clean→chunk→score→extract) now dispatched to thread pool via `loop.run_in_executor()` in all 3 call sites — keeps event loop unblocked for SSE/health | `src/core/agent/nodes.py`, `src/core/agents/researcher.py`, `src/core/agents/coordinator.py` | 2 hours | 🟡 Medium | ✅ Fixed |

---

## P2 — Dead Code & Stubs

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| B12 | Legacy synchronous `SearchTool` — not imported anywhere | `src/tools/search_tool.py` | 5 min | 🟢 Low | ✅ Deprecated — `main.py` updated to use `ResearchOrchestrator`; `src/tools/__init__.py` marks package deprecated |
| B13 | Legacy `CrawlTool` — not imported anywhere | `src/tools/crawl_tool.py` | 5 min | 🟢 Low | ✅ Deprecated — see B12 |
| B14 | Knowledge graph module fully implemented but never integrated | `src/knowledge/*` | N/A (integration is I13) | 🟢 Low | ✅ Fixed (via I13) |
| B15 | `ArxivService` fully implemented but never used in pipeline | `src/services/search/arxiv.py` | N/A (integration is I12) | 🟢 Low | ✅ Fixed (via I12) |

---

## P3 — Architectural Improvements (Future)

| ID | Description | Files Affected | Effort | Risk | Status |
|----|-------------|----------------|--------|------|--------|
| I11 | Unified V1 API — V2 multi-agent engine merged into single router at `/api/v1/research`; old V1 LangGraph router unmounted; session persistence, follow-up, transform, conversation tree endpoints preserved; frontend + tests + docs updated | `src/api/routes/research_unified.py`, `__init__.py`, `app.py`, `frontend/lib/api-service.ts` | 1–2 days | 🟡 Medium | ✅ Fixed |
| I12 | ArXiv API wired into `_academic_search()` — native `ArxivService` queries + web-search fallback; deduplication by URL | `src/core/agents/researcher.py`, `src/services/search/arxiv.py` | 4 hours | 🟢 Low | ✅ Fixed |
| I13 | Knowledge graph extraction integrated into coordinator `_phase_processing()` — `EntityExtractor` runs on top-3 docs; entities + relationships stored in `ResearchContext` | `src/core/agents/coordinator.py`, `src/knowledge/extraction.py` | 4 hours | 🟢 Low | ✅ Fixed |
| I14 | Use numpy for embedding operations | `src/services/embedding/service.py` | 1 hour | 🟢 Low | ✅ Fixed (via Perf-P1+P2) |
| I15 | ~~slowapi rate limiting~~ → Replaced with asyncio.Semaphore resource guard | `src/api/routes/research*.py` | 1 hour | 🟡 Medium | ✅ Fixed (via S4) |
| I16 | All 4 DB paths now configurable via `.env` — `DIOGENES_CACHE_DATABASE`, `DIOGENES_SESSION_DATABASE`, `DIOGENES_MEMORY_DATABASE`, `DIOGENES_CONVERSATION_DATABASE`; storage classes read from config when no explicit path given | `src/config.py`, `src/storage/*` | 30 min | 🟢 Low | ✅ Fixed |
| I17 | Multi-worker Uvicorn — `DIOGENES_API_WORKERS` config + auto-detect in production; `_resolve_workers()` in `run_api.py` | `run_api.py`, `src/api/app.py`, `src/config.py` | 15 min | 🟢 Low | ✅ Fixed |
| I18 | Batch contradiction detection into single LLM call | `src/core/agents/verifier.py` | 1 hour | 🟢 Low | ✅ Fixed (via Perf-P6) |
| I19 | WebSocket endpoint for real-time communication | `src/api/` | 4 hours | 🟢 Low | ⬜ TODO |
| I20 | Connection pooling — reuse httpx clients | `src/api/routes/health.py` | 30 min | 🟢 Low | ✅ Fixed (via Perf-P4) |
| I21 | Legacy tools deprecated — `main.py` updated to use `ResearchOrchestrator`; `src/tools/__init__.py` added with deprecation notice; old wrappers preserved for backward compat | `src/tools/__init__.py`, `main.py` | 5 min | 🟢 Low | ✅ Fixed |
| I22 | `JSONFormatter` added to `src/utils/logging.py` — enable via `DIOGENES_LOG_JSON_FORMAT=true`; emits single-line JSON with timestamp, level, logger, message, exception, and context fields | `src/utils/logging.py`, `src/config.py` | 1 hour | 🟢 Low | ✅ Fixed |
| I23 | Prometheus metrics — `PrometheusMiddleware` records request count/latency histograms; research-specific counters + gauges; `/health/metrics` endpoint in Prometheus exposition format | `src/api/metrics.py`, `src/api/routes/health.py`, `src/api/app.py` | 2 hours | 🟢 Low | ✅ Fixed |

---

## Fix Order (Execution Sequence)

1. **P0 Runtime Crashes:** B1 → B2 → B3
2. **P0/P1 Security:** S2 → S3 → S6 → S7 → S8
3. **P1 Logic Errors:** B5 → B8 → B10 → B11 → B4 → B7
4. **P1 Config:** C4 → C1
5. **P1–P2 Performance:** Perf-P3 → Perf-P4 → Perf-P5 → Perf-P7
6. **P2 Architecture:** A5/I5
7. **P2 Dead Code:** B12 → B13
8. **P3 Improvements:** Deferred pending team review

> **Note:** S1/S4/S5 have been reimagined for FOSS-local-first (no OAuth/JWT/RBAC). B9 fixed via C1. C2/C3 now validated at startup. B6 (PDF loader) wired in. S9 (HTTPS) handled via `verify_ssl` config + startup warnings. I16 (DB paths), I17 (multi-worker), I22 (JSON logging) all completed. I11 (V1/V2 unification), I12 (ArXiv API), I13 (knowledge graph), I21 (legacy tools deprecated), I23 (Prometheus metrics) all completed. Remaining future item: I19 (WebSocket).

---

*Derived exclusively from BACKEND_DEEP_ANALYSIS.md. No new issues added.*
