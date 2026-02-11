# Diogenes Project - Comprehensive Error Analysis Report

**Generated:** February 1, 2026  
**Version Analyzed:** 2.0.0  
**Purpose:** Pre-launch FOSS Quality Audit

---

## Executive Summary

This report identifies **23 issues** across the Diogenes codebase, categorized by severity:
- 🔴 **Critical (5):** Prevent normal operation
- 🟠 **High (7):** Significant bugs or security concerns
- 🟡 **Medium (8):** Functionality issues or inconsistencies
- 🟢 **Low (3):** Minor improvements and polish

---

## 🔴 CRITICAL ISSUES (Must Fix Before Launch)

### 1. Health Endpoint Path Mismatch (Startup Script Failure)

**Location:** 
- [start-diogenes.ps1](start-diogenes.ps1) - Line 8
- [src/api/app.py](src/api/app.py#L135) - Line 135
- [src/api/routes/health.py](src/api/routes/health.py#L21) - Line 21

**Problem:**  
The startup script checks `http://localhost:8000/api/v1/health/` but the actual health endpoint is at `http://localhost:8000/health/`.

**Analysis:**
- `health.py` defines router with `prefix="/health"`
- `app.py` includes router with NO additional prefix: `app.include_router(health_router)`
- Therefore: endpoint is at `/health/`, NOT `/api/v1/health/`

**Impact:** Startup script always reports "Backend failed to start" even when backend is running.

**Fix:**
```python
# Option A: Change start-diogenes.ps1 (line 8)
$backendHealthUrl = "http://localhost:$backendPort/health/"

# Option B: Change app.py (line 135) to add prefix
app.include_router(health_router, prefix="/api/v1")  # Add prefix
```

**Recommendation:** Use Option A (fix script) to maintain backward compatibility.

---

### 2. Frontend TypeScript Compilation Error

**Location:** [frontend/lib/api-service.ts](frontend/lib/api-service.ts#L27) - Line 27

**Problem:**
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
```

**Error:** `Property 'env' does not exist on type 'ImportMeta'`.

**Cause:** Missing Vite client types in TypeScript configuration.

**Fix:** Add to `frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "types": ["vite/client"]
  }
}
```

**Impact:** Frontend may fail to build in strict TypeScript environments.

---

### 3. Frontend Health Check URL Inconsistency

**Location:** [frontend/lib/api-service.ts](frontend/lib/api-service.ts#L137) - Line 137

**Problem:**
```typescript
async health(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${this.baseUrl}/v1/health/`);
  // ...
}
```

**Analysis:**
- `this.baseUrl` = `http://localhost:8000/api`
- Constructed URL: `http://localhost:8000/api/v1/health/`
- Actual endpoint: `http://localhost:8000/health/`

**Fix:**
```typescript
async health(): Promise<{ status: string; version: string }> {
  // Remove baseUrl prefix, use absolute path
  const response = await fetch('http://localhost:8000/health/');
  // ...
}
```

**Impact:** Frontend health checks always fail.

---

### 4. CORS Configuration Missing Frontend Port 5173

**Location:** [config/default.yaml](config/default.yaml#L61) - Line 61

**Problem:**
```yaml
api:
  cors_origins:
    - "http://localhost:3000"  # Only port 3000 listed
```

**Analysis:** Frontend runs on port 5173 (Vite default), but CORS only allows port 3000.

**Fix:**
```yaml
api:
  cors_origins:
    - "http://localhost:3000"
    - "http://localhost:5173"
    - "http://127.0.0.1:5173"
```

**Impact:** Frontend cannot communicate with backend due to CORS blocking.

---

### 5. Missing `@types/react` and `@types/react-dom` Dependencies

**Location:** [frontend/package.json](frontend/package.json)

**Problem:** Package.json is missing TypeScript type definitions.

**Fix:** Add to devDependencies:
```json
{
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0"
  }
}
```

**Impact:** TypeScript errors for React components; IDE IntelliSense broken.

---

## 🟠 HIGH SEVERITY ISSUES

### 6. Invoke-WebRequest Timeout Issue on Windows

**Location:** [start-diogenes.ps1](start-diogenes.ps1)

**Problem:** PowerShell's `Invoke-RestMethod` with `TimeoutSec 2` is often insufficient for cold-start health checks.

**Fix:**
```powershell
# Increase timeout to 5 seconds
$response = Invoke-RestMethod -Uri $backendHealthUrl -Method GET -TimeoutSec 5 -ErrorAction Stop
```

**Impact:** False negatives on slow systems or first-time startup.

---

### 7. In-Memory Session Storage (Non-Persistent)

**Location:** [src/api/routes/research.py](src/api/routes/research.py#L43) - Line 43

**Problem:**
```python
# In-memory session storage (replace with persistent storage in production)
_sessions: dict[str, dict] = {}
```

**Analysis:** Sessions are lost on server restart. Comment says "replace with persistent storage in production" but this is the only implementation.

**Fix:** Use the existing `SessionStore` from `src/storage/session.py` or SQLite backend.

**Impact:** Research sessions lost on restart; not production-ready.

---

### 8. API v1 vs v2 Inconsistent Endpoints

**Location:** 
- [src/api/app.py](src/api/app.py#L133-L136)
- [frontend/lib/api-service.ts](frontend/lib/api-service.ts)

**Problem:** Multiple API versions with unclear routing:
```python
app.include_router(research_router, prefix="/api/v1")      # v1: /api/v1/research/
app.include_router(research_v2_router, prefix="/api/v1")    # v2 (now unified under v1): /api/v1/research/
```

**Analysis:**
- Frontend uses `/api/v1/research/` (unified)
- Health check uses `/api/v1/health/` (correct)
- All paths now under `/api/v1/`

**Fix:** Unified to single v1 API. Both versions now served under `/api/v1/`.

---

### 9. Unclosed HTTP Clients (Resource Leak)

**Location:** 
- [src/services/search/searxng.py](src/services/search/searxng.py#L48)
- [src/services/llm/ollama.py](src/services/llm/ollama.py#L53)

**Problem:** `httpx.AsyncClient` instances are created but `close()` is never called in the application lifecycle.

**Fix:** Use context manager or call `close()` in FastAPI lifespan shutdown:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    services = get_services()
    await services.search_service.close()
    await services.llm_service.close()
```

**Impact:** Connection pool exhaustion in long-running servers.

---

### 10. Quality Score Validation Not Enforced in Schema

**Location:** [src/api/schemas/research.py](src/api/schemas)

**Problem:** Quality scores are clamped in multiple places (citation manager, research routes) but the Pydantic schema doesn't enforce the constraint.

**Fix:** Add validator:
```python
from pydantic import Field, validator

class Source(BaseModel):
    quality_score: float = Field(ge=0.0, le=1.0, default=0.0)
```

**Impact:** Inconsistent validation; potential for out-of-range values to reach frontend.

---

### 11. Missing Error Handling in SSE Streaming

**Location:** [frontend/lib/api-service.ts](frontend/lib/api-service.ts#L82-L130)

**Problem:** SSE parsing doesn't handle malformed events or network errors gracefully.

**Fix:** Add try-catch around JSON parsing and handle connection drops:
```typescript
try {
  const data = JSON.parse(line.substring(5).trim());
  // ...
} catch (e) {
  console.warn('Malformed SSE event:', line);
  continue;
}
```

**Impact:** Frontend may crash on malformed SSE events.

---

### 12. Hardcoded LLM Model Names in default.yaml

**Location:** [config/default.yaml](config/default.yaml#L31-L35)

**Problem:**
```yaml
models:
  planner: "gpt-oss:20b-cloud"
  extractor: "gpt-oss:20b-cloud"
  synthesizer: "gpt-oss:20b-cloud"
  reflector: "gpt-oss:20b-cloud"
```

**Analysis:** These model names are non-standard and may not exist in typical Ollama installations. The Python defaults in `config.py` use different models (`qwen2.5:3b`, `llama3.1:8b`).

**Fix:** Update to commonly available models:
```yaml
models:
  planner: "qwen2.5:3b"
  extractor: "qwen2.5:3b"
  synthesizer: "llama3.1:8b"
  reflector: "llama3.1:8b"
```

**Impact:** Research fails with "model not found" on standard Ollama installations.

---

## 🟡 MEDIUM SEVERITY ISSUES

### 13. Frontend Source Type Mismatch

**Location:** 
- [frontend/demo.tsx](frontend/demo.tsx#L56-L61)
- [frontend/lib/api-types.ts](frontend/lib/api-types.ts#L5-L10)

**Problem:** Frontend defines two different `Source` interfaces:
```typescript
// demo.tsx (local)
interface Source {
  url: string;
  title: string;
  domain: string;
  quality_score?: number;
}

// api-types.ts (from backend)
export interface Source {
  index: number;
  title: string;
  url: string;
  domain: string;
  quality_score: number;
}
```

**Fix:** Use only the api-types.ts `Source` type throughout.

---

### 14. Missing Tailwind CSS Types

**Location:** [frontend/package.json](frontend/package.json)

**Problem:** `tailwindcss` and `@tailwindcss/typography` are used but not in dependencies.

**Fix:** Add to devDependencies:
```json
{
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

---

### 15. Research Mode Enum Inconsistency

**Location:**
- [frontend/demo.tsx](frontend/demo.tsx#L93)
- [src/core/agent/modes.py](src/core/agent/modes.py)

**Problem:** Frontend uses modes `['quick', 'balanced', 'deep']` but backend has more modes: `['quick', 'balanced', 'full', 'research', 'deep']`.

**Fix:** Align frontend with backend's full set of modes, or clearly document which modes are user-facing vs internal.

---

### 16. No Input Sanitization on Query

**Location:** [src/api/routes/research.py](src/api/routes/research.py#L168)

**Problem:** User queries are passed directly to LLM prompts without sanitization.

**Fix:** Add input validation:
```python
from pydantic import Field, validator

class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    
    @validator('query')
    def sanitize_query(cls, v):
        # Remove potential prompt injection patterns
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Query too short')
        return v
```

---

### 17. Memory Store Not Initialized in Orchestrator

**Location:** [src/core/agents/orchestrator.py](src/core/agents/orchestrator.py#L169)

**Problem:**
```python
self._memory_store: Optional[MemoryStore] = None
# ...
if self._memory_store:  # Always None unless manually set
    memory_context = await self._memory_store.build_context_string(...)
```

**Analysis:** Memory store is declared but never initialized in `initialize()`.

**Fix:** Add to `initialize()`:
```python
async def initialize(self) -> None:
    # ... existing code ...
    self._memory_store = MemoryStore()
    await self._memory_store.initialize()
```

---

### 18. Conversation Tree Not Imported in Routes

**Location:** [src/api/routes/research.py](src/api/routes/research.py#L509)

**Problem:**
```python
from src.storage import get_conversation_tree  # This function may not exist
```

**Analysis:** The import `get_conversation_tree` may not be exported from `src/storage/__init__.py`.

**Fix:** Ensure proper export in `src/storage/__init__.py`:
```python
from src.storage.conversation import ConversationTree, get_conversation_tree
```

---

### 19. Unused Google Genai Dependency

**Location:** [frontend/package.json](frontend/package.json#L12)

**Problem:**
```json
"@google/genai": "^1.34.0"
```

**Analysis:** This dependency was for the old Gemini integration but is no longer used after backend integration.

**Fix:** Remove unused dependency:
```bash
npm uninstall @google/genai
```

---

### 20. Missing Request Timeout in Frontend Fetch

**Location:** [frontend/lib/api-service.ts](frontend/lib/api-service.ts#L36)

**Problem:** Fetch calls have no timeout configured.

**Fix:** Add AbortController with timeout:
```typescript
async research(request: ResearchRequest): Promise<ResearchResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 min timeout
  
  try {
    const response = await fetch(`${this.baseUrl}/v1/research/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: request.query, mode: request.mode }),
      signal: controller.signal
    });
    // ...
  } finally {
    clearTimeout(timeoutId);
  }
}
```

---

## 🟢 LOW SEVERITY ISSUES

### 21. Duplicate Error Logging

**Location:** Multiple files in `src/api/routes/`

**Problem:** Errors are logged in both the route handlers and global exception handlers, causing duplicate log entries.

**Fix:** Remove logging from route handlers or mark as `debug` level.

---

### 22. Inconsistent Date Formatting

**Location:**
- Backend uses `datetime.utcnow().isoformat()`
- Frontend expects `created_at: string`

**Problem:** No timezone information in ISO strings.

**Fix:** Use timezone-aware datetimes:
```python
from datetime import datetime, timezone
datetime.now(timezone.utc).isoformat()
```

---

### 23. Missing Favicon for Source Cards

**Location:** [src/api/schemas/research.py](src/api/schemas)

**Problem:** `Source` schema includes `favicon_url` but it's often `None` and frontend falls back to Google's favicon service.

**Fix:** Set default in backend:
```python
@property
def favicon_url(self) -> str:
    return f"https://www.google.com/s2/favicons?domain={self.domain}&sz=64"
```

---

## Improvement Recommendations

### Security Hardening
1. Add rate limiting to API endpoints
2. Implement CSRF protection
3. Add request body size limits
4. Sanitize all user inputs before LLM prompts
5. Add authentication/API key support (optional)

### Performance Optimization
1. Implement result caching in Redis
2. Add connection pooling for HTTP clients
3. Optimize LLM prompt sizes
4. Add request queuing for high load

### Developer Experience
1. Add OpenAPI documentation enhancements
2. Create Docker development container
3. Add pre-commit hooks for linting
4. Create contribution-ready GitHub Actions

### Production Readiness
1. Add health check for all dependent services
2. Implement graceful shutdown
3. Add structured logging (JSON format)
4. Create Kubernetes deployment manifests
5. Add Prometheus metrics endpoint

---

## Quick Fix Priority Order

1. **Fix health endpoint URL** - Immediate (startup script failure)
2. **Add CORS origin for port 5173** - Immediate (frontend-backend communication)
3. **Fix TypeScript compilation** - Before build
4. **Update default LLM models** - Before first run
5. **Add persistent session storage** - Before production

---

## Summary Table

| # | Severity | Issue | Location | Effort |
|---|----------|-------|----------|--------|
| 1 | 🔴 Critical | Health endpoint mismatch | start-diogenes.ps1 | 5 min |
| 2 | 🔴 Critical | TS compilation error | api-service.ts | 2 min |
| 3 | 🔴 Critical | Frontend health URL | api-service.ts | 2 min |
| 4 | 🔴 Critical | CORS missing port 5173 | default.yaml | 1 min |
| 5 | 🔴 Critical | Missing React types | package.json | 2 min |
| 6 | 🟠 High | PowerShell timeout | start-diogenes.ps1 | 2 min |
| 7 | 🟠 High | In-memory sessions | research.py | 30 min |
| 8 | 🟠 High | API version confusion | app.py | 15 min |
| 9 | 🟠 High | Unclosed HTTP clients | services | 20 min |
| 10 | 🟠 High | Quality score schema | schemas | 5 min |
| 11 | 🟠 High | SSE error handling | api-service.ts | 15 min |
| 12 | 🟠 High | Wrong default LLM models | default.yaml | 2 min |
| 13 | 🟡 Medium | Source type mismatch | demo.tsx | 10 min |
| 14 | 🟡 Medium | Missing Tailwind deps | package.json | 5 min |
| 15 | 🟡 Medium | Mode enum mismatch | demo.tsx | 10 min |
| 16 | 🟡 Medium | No query sanitization | research.py | 20 min |
| 17 | 🟡 Medium | Memory store init | orchestrator.py | 10 min |
| 18 | 🟡 Medium | Missing import | research.py | 5 min |
| 19 | 🟡 Medium | Unused dependency | package.json | 2 min |
| 20 | 🟡 Medium | No fetch timeout | api-service.ts | 10 min |
| 21 | 🟢 Low | Duplicate logging | routes | 15 min |
| 22 | 🟢 Low | Date formatting | multiple | 10 min |
| 23 | 🟢 Low | Favicon default | schemas | 5 min |

**Total Estimated Fix Time:** ~4-5 hours for all issues

---

## Next Steps

1. Address all 🔴 Critical issues first (15-20 minutes)
2. Fix 🟠 High severity issues before launch (1-2 hours)
3. Schedule 🟡 Medium issues for post-launch patches
4. Add 🟢 Low severity fixes to backlog

---

*Report generated by comprehensive codebase analysis.*
