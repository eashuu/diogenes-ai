# Diogenes API Specification

## Overview

The Diogenes API provides a RESTful interface for conducting AI-powered research. All endpoints support both synchronous and streaming modes.

**Base URL:** `http://localhost:8000/api/v1`

---

## Authentication

*Note: Authentication is optional for local deployments. Can be enabled via configuration.*

```yaml
# config/production.yaml
api:
  auth:
    enabled: true
    type: "bearer"  # or "api_key"
```

---

## Endpoints

### 1. Research

#### POST /research

Start a new research query.

**Request:**
```json
{
  "query": "string (required)",
  "options": {
    "focus_mode": "general | academic | news | code",
    "max_sources": 5,
    "max_iterations": 3,
    "language": "en",
    "time_range": "day | week | month | year | all"
  },
  "session_id": "string | null"
}
```

**Response (200 OK):**
```json
{
  "session_id": "sess_a1b2c3d4",
  "answer": "Based on my research...[1]...[2]...",
  "sources": [
    {
      "index": 1,
      "url": "https://example.com/article",
      "title": "Article Title",
      "domain": "example.com",
      "favicon": "https://example.com/favicon.ico",
      "snippet": "Preview of the content...",
      "quality_score": 0.87,
      "crawled_at": "2026-01-25T10:30:00Z"
    }
  ],
  "related_questions": [
    "What are the implications of...?",
    "How does this compare to...?"
  ],
  "metadata": {
    "query": "original query",
    "sub_queries": ["sub1", "sub2"],
    "sources_searched": 15,
    "sources_crawled": 5,
    "iterations": 1,
    "tokens_used": 2340,
    "time_elapsed_ms": 12500,
    "model": "llama3.1:8b"
  }
}
```

**Error Response (4xx/5xx):**
```json
{
  "error": {
    "code": "SEARCH_FAILED",
    "message": "Unable to complete search",
    "details": "SearXNG connection timeout"
  }
}
```

---

#### GET /research/stream

Stream research results via Server-Sent Events (SSE).

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Research query |
| focus_mode | string | No | Focus mode (default: general) |
| max_sources | int | No | Max sources to crawl (default: 5) |
| session_id | string | No | Continue existing session |

**SSE Events:**

```
event: status
data: {"phase": "planning", "message": "Analyzing your query..."}

event: plan
data: {"sub_queries": ["query1", "query2"]}

event: status
data: {"phase": "searching", "message": "Searching 2 queries..."}

event: search_progress
data: {"completed": 1, "total": 2, "results_found": 8}

event: status
data: {"phase": "crawling", "message": "Reading 5 sources..."}

event: crawl_progress
data: {"completed": 3, "total": 5, "url": "https://..."}

event: sources
data: [
  {"index": 1, "title": "...", "url": "...", "domain": "...", "favicon": "..."},
  {"index": 2, "title": "...", "url": "...", "domain": "...", "favicon": "..."}
]

event: status
data: {"phase": "synthesizing", "message": "Generating answer..."}

event: token
data: "The"

event: token
data: " latest"

event: token
data: " research"

event: citation
data: {"text": "[1]", "source_index": 1}

event: token
data: " shows"

event: related
data: ["Follow-up question 1?", "Follow-up question 2?"]

event: done
data: {
  "session_id": "sess_abc123",
  "metadata": {
    "tokens_used": 2340,
    "time_elapsed_ms": 12500
  }
}
```

**Error Event:**
```
event: error
data: {"code": "LLM_TIMEOUT", "message": "Model inference timed out", "recoverable": true}
```

---

### 2. Sessions

#### GET /sessions/{session_id}

Retrieve a previous research session.

**Response (200 OK):**
```json
{
  "session_id": "sess_abc123",
  "created_at": "2026-01-25T10:00:00Z",
  "updated_at": "2026-01-25T10:05:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What are quantum computers?",
      "timestamp": "2026-01-25T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Quantum computers are...[1]...",
      "sources": [...],
      "timestamp": "2026-01-25T10:00:30Z"
    }
  ],
  "all_sources": [...]
}
```

---

#### POST /sessions/{session_id}/followup

Continue a research session with a follow-up question.

**Request:**
```json
{
  "query": "Can you elaborate on the second point?",
  "options": {
    "use_existing_sources": true,
    "search_new": true
  }
}
```

**Response:** Same as POST /research

---

#### DELETE /sessions/{session_id}

Delete a session and its associated data.

**Response (204 No Content)**

---

### 3. Sources

#### GET /sources/{session_id}

Get all sources used in a session.

**Response (200 OK):**
```json
{
  "sources": [
    {
      "index": 1,
      "url": "https://...",
      "title": "...",
      "domain": "...",
      "favicon": "...",
      "snippet": "...",
      "full_content": "Full markdown content...",
      "quality_score": 0.87,
      "citations": [
        {"position": 45, "claim": "The sky is blue"},
        {"position": 120, "claim": "Water is wet"}
      ]
    }
  ]
}
```

---

#### GET /sources/{session_id}/{source_index}

Get a specific source with full content.

**Response (200 OK):**
```json
{
  "index": 1,
  "url": "https://...",
  "title": "...",
  "full_content": "...",
  "metadata": {
    "author": "...",
    "published_date": "...",
    "word_count": 1500
  }
}
```

---

### 4. Health & Status

#### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "searxng": {"status": "up", "latency_ms": 45},
    "ollama": {"status": "up", "latency_ms": 12, "models": ["llama3.1:8b"]},
    "cache": {"status": "up", "entries": 1234}
  }
}
```

---

#### GET /status

Detailed system status.

**Response (200 OK):**
```json
{
  "uptime_seconds": 3600,
  "requests_total": 150,
  "requests_active": 2,
  "cache": {
    "search_hits": 45,
    "search_misses": 30,
    "crawl_hits": 120,
    "crawl_misses": 50
  },
  "resources": {
    "memory_mb": 512,
    "cpu_percent": 15
  }
}
```

---

### 5. Configuration (Admin)

#### GET /config

Get current configuration (non-sensitive).

**Response (200 OK):**
```json
{
  "search": {
    "provider": "searxng",
    "max_results": 10,
    "cache_ttl": 3600
  },
  "llm": {
    "provider": "ollama",
    "models": {
      "synthesizer": "llama3.1:8b",
      "planner": "qwen2.5:3b"
    }
  },
  "agent": {
    "max_iterations": 3,
    "coverage_threshold": 0.7
  }
}
```

---

#### PATCH /config

Update configuration at runtime.

**Request:**
```json
{
  "llm.models.synthesizer": "llama3.1:70b",
  "agent.max_iterations": 5
}
```

**Response (200 OK):**
```json
{
  "updated": ["llm.models.synthesizer", "agent.max_iterations"],
  "restart_required": false
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_QUERY | 400 | Query is empty or malformed |
| SESSION_NOT_FOUND | 404 | Session ID does not exist |
| SEARCH_FAILED | 502 | Search provider error |
| CRAWL_FAILED | 502 | Web crawling error |
| LLM_ERROR | 502 | LLM inference error |
| LLM_TIMEOUT | 504 | LLM response timed out |
| RATE_LIMITED | 429 | Too many requests |
| CONFIG_ERROR | 500 | Configuration error |
| INTERNAL_ERROR | 500 | Unexpected internal error |

---

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| /research | 10 | per minute |
| /research/stream | 10 | per minute |
| /sessions/* | 60 | per minute |
| /sources/* | 120 | per minute |

Rate limit headers:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1706180000
```

---

## WebSocket API (Future)

*Reserved for real-time bidirectional communication.*

```
ws://localhost:8000/ws/research

// Client -> Server
{"type": "start", "query": "...", "options": {...}}
{"type": "stop"}
{"type": "followup", "query": "..."}

// Server -> Client
{"type": "status", "data": {...}}
{"type": "token", "data": "..."}
{"type": "sources", "data": [...]}
{"type": "done", "data": {...}}
{"type": "error", "data": {...}}
```

---

## SDK Examples

### Python
```python
import httpx
from sseclient import SSEClient

# Streaming example
def stream_research(query: str):
    with httpx.stream("GET", f"{BASE_URL}/research/stream", params={"query": query}) as response:
        client = SSEClient(response)
        for event in client.events():
            if event.event == "token":
                print(event.data, end="", flush=True)
            elif event.event == "sources":
                sources = json.loads(event.data)
                print(f"\n\nSources: {len(sources)}")
            elif event.event == "done":
                print("\n\nComplete!")
                break
```

### JavaScript/TypeScript
```typescript
const eventSource = new EventSource(`${BASE_URL}/research/stream?query=${encodeURIComponent(query)}`);

eventSource.addEventListener("token", (e) => {
  process.stdout.write(e.data);
});

eventSource.addEventListener("sources", (e) => {
  const sources = JSON.parse(e.data);
  console.log("\nSources:", sources.length);
});

eventSource.addEventListener("done", (e) => {
  console.log("\nComplete!");
  eventSource.close();
});

eventSource.addEventListener("error", (e) => {
  console.error("Error:", e);
  eventSource.close();
});
```

### cURL
```bash
# Non-streaming
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum computing?"}'

# Streaming
curl -N http://localhost:8000/api/v1/research/stream?query=What%20is%20quantum%20computing
```

---

*API Version: 1.0*  
*Last Updated: January 25, 2026*
