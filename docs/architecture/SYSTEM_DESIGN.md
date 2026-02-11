# Diogenes System Design & Architecture

## Executive Summary

Diogenes is a **privacy-first, local-first AI research assistant** that replicates and improves upon Perplexity's capabilities using open-source tools. This document outlines the complete backend architecture designed for reliability, performance, and extensibility.

---

## 1. Design Principles

### 1.1 Core Principles

| Principle | Description |
|-----------|-------------|
| **Privacy First** | All processing happens locally; no data leaves the user's environment |
| **Streaming Native** | Every component supports streaming for real-time UX |
| **Citation Integrity** | Every claim must be traceable to a source |
| **Graceful Degradation** | System continues with partial results on failures |
| **Idempotent Operations** | Same input produces same output; safe retries |
| **Observable** | Comprehensive logging and metrics at every layer |

### 1.2 Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Query-to-first-token | < 3 seconds |
| Full response time | < 30 seconds (5 sources) |
| Concurrent users | 10+ (local deployment) |
| Memory footprint | < 4GB (excluding LLM) |
| Cache hit ratio | > 60% for repeated queries |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER (FastAPI)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ /research   │  │ /stream     │  │ /sources    │  │ /session            │ │
│  │ POST        │  │ SSE         │  │ GET         │  │ GET/POST            │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER (LangGraph)                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        ResearchAgent (State Machine)                  │   │
│  │                                                                       │   │
│  │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐   │   │
│  │   │ PLAN    │───▶│ SEARCH  │───▶│ PROCESS │───▶│ SYNTHESIZE      │   │   │
│  │   │         │    │         │    │         │    │ (Stream)        │   │   │
│  │   └─────────┘    └────┬────┘    └─────────┘    └─────────────────┘   │   │
│  │        ▲              │                                               │   │
│  │        │              ▼                                               │   │
│  │        │         ┌─────────┐                                          │   │
│  │        └─────────│ REFLECT │ (Need more info?)                        │   │
│  │                  └─────────┘                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
┌─────────────────────────┐ ┌──────────────────┐ ┌─────────────────────────┐
│    RETRIEVAL LAYER      │ │  PROCESSING      │ │   INFERENCE LAYER       │
│                         │ │  LAYER           │ │                         │
│ ┌─────────────────────┐ │ │ ┌──────────────┐ │ │ ┌─────────────────────┐ │
│ │ SearchService       │ │ │ │ Chunker      │ │ │ │ LLMService          │ │
│ │ (SearXNG)           │ │ │ └──────────────┘ │ │ │ (Ollama)            │ │
│ └─────────────────────┘ │ │ ┌──────────────┐ │ │ │ - Planner           │ │
│ ┌─────────────────────┐ │ │ │ Extractor    │ │ │ │ - Synthesizer       │ │
│ │ CrawlService        │ │ │ │ (Facts)      │ │ │ │ - Extractor         │ │
│ │ (crawl4ai)          │ │ │ └──────────────┘ │ │ └─────────────────────┘ │
│ └─────────────────────┘ │ │ ┌──────────────┐ │ │ ┌─────────────────────┐ │
│ ┌─────────────────────┐ │ │ │ CitationMgr  │ │ │ │ EmbeddingService    │ │
│ │ ContentFilter       │ │ │ └──────────────┘ │ │ │ (nomic-embed-text)  │ │
│ └─────────────────────┘ │ │ ┌──────────────┐ │ │ └─────────────────────┘ │
│                         │ │ │ QualityScorer│ │ │                         │
└─────────────────────────┘ │ └──────────────┘ │ └─────────────────────────┘
                           └──────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PERSISTENCE LAYER                                 │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ SessionStore    │  │ CacheStore      │  │ VectorStore (Future)        │  │
│  │ (SQLite)        │  │ (SQLite/Redis)  │  │ (ChromaDB)                  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                  │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                                   │
│  │ SearXNG         │  │ Ollama          │                                   │
│  │ (Docker:8080)   │  │ (localhost:11434)│                                  │
│  └─────────────────┘  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
diogenes/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Configuration management
│   │
│   ├── api/                       # API Layer
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── research.py        # /research endpoints
│   │   │   ├── sources.py         # /sources endpoints
│   │   │   └── session.py         # /session endpoints
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── request.py         # Pydantic request models
│   │   │   └── response.py        # Pydantic response models
│   │   └── dependencies.py        # FastAPI dependencies
│   │
│   ├── core/                      # Core Business Logic
│   │   ├── __init__.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py           # LangGraph state machine
│   │   │   ├── nodes.py           # Graph nodes (plan, search, process, synthesize)
│   │   │   ├── state.py           # Agent state definition
│   │   │   └── prompts.py         # All prompts centralized
│   │   ├── research/
│   │   │   ├── __init__.py
│   │   │   ├── planner.py         # Query decomposition
│   │   │   ├── synthesizer.py     # Answer synthesis with streaming
│   │   │   └── reflector.py       # Reflection/decision logic
│   │   └── citation/
│   │       ├── __init__.py
│   │       ├── manager.py         # Citation tracking
│   │       └── formatter.py       # Citation formatting [1], [2]
│   │
│   ├── services/                  # External Service Integrations
│   │   ├── __init__.py
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract search interface
│   │   │   ├── searxng.py         # SearXNG implementation
│   │   │   └── models.py          # Search result models
│   │   ├── crawl/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract crawl interface
│   │   │   ├── crawl4ai.py        # crawl4ai implementation
│   │   │   └── models.py          # Crawl result models
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract LLM interface
│   │   │   ├── ollama.py          # Ollama implementation
│   │   │   └── models.py          # LLM config models
│   │   └── embedding/
│   │       ├── __init__.py
│   │       ├── base.py            # Abstract embedding interface
│   │       └── ollama.py          # Ollama embeddings
│   │
│   ├── processing/                # Content Processing
│   │   ├── __init__.py
│   │   ├── chunker.py             # Smart text chunking
│   │   ├── extractor.py           # Fact/entity extraction
│   │   ├── cleaner.py             # HTML/content cleaning
│   │   └── scorer.py              # Source quality scoring
│   │
│   ├── storage/                   # Persistence Layer
│   │   ├── __init__.py
│   │   ├── session.py             # Session management
│   │   ├── cache.py               # Search/crawl caching
│   │   └── models.py              # SQLAlchemy models
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── logging.py             # Structured logging
│       ├── metrics.py             # Performance metrics
│       ├── retry.py               # Retry logic with backoff
│       └── streaming.py           # Streaming utilities
│
├── tests/                         # Test Suite
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/
│   │   ├── test_chunker.py
│   │   ├── test_extractor.py
│   │   └── test_citation.py
│   ├── integration/
│   │   ├── test_search.py
│   │   ├── test_crawl.py
│   │   └── test_agent.py
│   └── e2e/
│       └── test_research_flow.py
│
├── docs/                          # Documentation
│   ├── SYSTEM_DESIGN.md           # This document
│   ├── API.md                     # API documentation
│   └── DEPLOYMENT.md              # Deployment guide
│
├── docker/                        # Docker configurations
│   ├── Dockerfile                 # Main application
│   └── docker-compose.yml         # Full stack
│
├── config/                        # Configuration files
│   ├── default.yaml               # Default configuration
│   ├── development.yaml           # Dev overrides
│   └── production.yaml            # Prod overrides
│
├── scripts/                       # Utility scripts
│   ├── setup.py                   # Initial setup
│   └── benchmark.py               # Performance benchmarks
│
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Dev dependencies
├── pyproject.toml                 # Project configuration
└── README.md                      # Project README
```

---

## 4. Component Specifications

### 4.1 Agent State Machine (LangGraph)

The research agent follows a ReAct-style loop with explicit state transitions:

```
                    ┌─────────────────────────────┐
                    │         START               │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │         PLAN                │
                    │  - Decompose query          │
                    │  - Generate search queries  │
                    │  - Identify focus areas     │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
            ┌──────▶│         SEARCH              │
            │       │  - Execute SearXNG queries  │
            │       │  - Rank results             │
            │       │  - Select URLs to crawl     │
            │       └─────────────┬───────────────┘
            │                     │
            │                     ▼
            │       ┌─────────────────────────────┐
            │       │         CRAWL               │
            │       │  - Parallel page fetching   │
            │       │  - Content extraction       │
            │       │  - Error handling           │
            │       └─────────────┬───────────────┘
            │                     │
            │                     ▼
            │       ┌─────────────────────────────┐
            │       │         PROCESS             │
            │       │  - Chunk content            │
            │       │  - Extract facts            │
            │       │  - Build citation map       │
            │       │  - Score quality            │
            │       └─────────────┬───────────────┘
            │                     │
            │                     ▼
            │       ┌─────────────────────────────┐
            │       │         REFLECT             │
            │       │  - Evaluate coverage        │◀─────┐
            │       │  - Identify gaps            │      │
            │       │  - Decide: enough or more?  │      │
            │       └─────────────┬───────────────┘      │
            │                     │                      │
            │         ┌───────────┴───────────┐          │
            │         │                       │          │
            │    [ENOUGH]                [NEED MORE]     │
            │         │                       │          │
            │         ▼                       └──────────┘
            │       ┌─────────────────────────────┐
            └───────│         SYNTHESIZE          │
         (retry on  │  - Stream answer            │
          failure)  │  - Insert citations         │
                    │  - Generate follow-ups      │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │         END                 │
                    └─────────────────────────────┘
```

#### State Definition

```python
@dataclass
class ResearchState:
    # Input
    query: str
    session_id: str
    focus_mode: FocusMode = FocusMode.GENERAL
    
    # Planning
    sub_queries: List[str] = field(default_factory=list)
    search_plan: SearchPlan = None
    
    # Search Results
    search_results: List[SearchResult] = field(default_factory=list)
    selected_urls: List[str] = field(default_factory=list)
    
    # Crawled Content
    crawled_pages: List[CrawledPage] = field(default_factory=list)
    failed_urls: List[str] = field(default_factory=list)
    
    # Processed Content
    chunks: List[ContentChunk] = field(default_factory=list)
    facts: List[ExtractedFact] = field(default_factory=list)
    citations: CitationMap = field(default_factory=CitationMap)
    
    # Reflection
    iteration: int = 0
    max_iterations: int = 3
    coverage_score: float = 0.0
    gaps: List[str] = field(default_factory=list)
    
    # Output
    answer: str = ""
    related_questions: List[str] = field(default_factory=list)
    
    # Metadata
    tokens_used: int = 0
    time_elapsed: float = 0.0
    errors: List[str] = field(default_factory=list)
```

---

### 4.2 Citation System

The citation system ensures every claim is traceable:

```
┌─────────────────────────────────────────────────────────────────┐
│                      CITATION PIPELINE                          │
│                                                                  │
│  Source Document                      Output with Citations      │
│  ┌─────────────────┐                  ┌─────────────────────────┐│
│  │ URL: example.com│                  │ The sky is blue [1].   ││
│  │ Title: Sky Info │     ──────▶      │ Water is wet [2].      ││
│  │ Content: ...    │                  │                        ││
│  │ Chunk ID: c_001 │                  │ Sources:               ││
│  └─────────────────┘                  │ [1] Sky Info - example ││
│                                       │ [2] Water Facts - wiki ││
│                                       └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

#### Citation Data Model

```python
@dataclass
class Source:
    id: str                    # Unique identifier
    url: str                   # Original URL
    title: str                 # Page title
    domain: str                # Extracted domain
    favicon: str               # Favicon URL
    snippet: str               # Representative snippet
    quality_score: float       # 0.0 - 1.0
    crawled_at: datetime
    content_hash: str          # For deduplication

@dataclass  
class Citation:
    index: int                 # Display index [1], [2], etc.
    source_id: str             # Reference to Source
    chunk_id: str              # Specific chunk used
    claim: str                 # The claim being cited
    confidence: float          # LLM confidence in attribution

@dataclass
class CitationMap:
    sources: Dict[str, Source]
    citations: List[Citation]
    
    def format_inline(self, text: str) -> str:
        """Insert [1], [2] markers into text"""
        
    def get_source_cards(self) -> List[SourceCard]:
        """Generate UI source cards"""
```

---

### 4.3 Streaming Architecture

All LLM outputs support streaming via Server-Sent Events (SSE):

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Client  │◀───│ FastAPI  │◀───│ LangGraph│◀───│  Ollama  │
│          │SSE │ /stream  │Async│ Agent   │Stream│         │
└──────────┘    └──────────┘    └──────────┘    └──────────┘

Event Types:
  - status:    {"type": "status", "message": "Searching..."}
  - sources:   {"type": "sources", "data": [source_cards]}
  - token:     {"type": "token", "data": "The"}
  - citation:  {"type": "citation", "data": {"index": 1, ...}}
  - related:   {"type": "related", "data": ["Question 1", ...]}
  - done:      {"type": "done", "metadata": {...}}
  - error:     {"type": "error", "message": "..."}
```

---

### 4.4 Search Service

```python
class SearchService(ABC):
    """Abstract interface for search providers"""
    
    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        categories: List[str] = None,
        time_range: TimeRange = None,
        language: str = "en"
    ) -> List[SearchResult]:
        pass

class SearXNGService(SearchService):
    """SearXNG implementation with retry and caching"""
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 20.0,
        max_retries: int = 3,
        cache: CacheStore = None
    ):
        pass
```

---

### 4.5 Crawl Service

```python
class CrawlService(ABC):
    """Abstract interface for web crawlers"""
    
    @abstractmethod
    async def crawl(
        self,
        urls: List[str],
        max_concurrent: int = 5,
        timeout: float = 30.0,
        extract_mode: ExtractMode = ExtractMode.MARKDOWN
    ) -> List[CrawlResult]:
        pass

class Crawl4AIService(CrawlService):
    """crawl4ai implementation with rate limiting"""
    
    async def crawl(self, urls: List[str], ...) -> List[CrawlResult]:
        """
        Features:
        - Parallel crawling with semaphore
        - Automatic retry on failure
        - Content type detection
        - JavaScript rendering
        - Rate limiting per domain
        """
        pass
```

---

### 4.6 LLM Service

```python
class LLMService(ABC):
    """Abstract interface for LLM providers"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        ...
    ) -> BaseModel:
        """Generate structured output matching schema"""
        pass

class OllamaService(LLMService):
    """Ollama implementation with model management"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.1:8b",
        fast_model: str = "qwen2.5:3b",  # For quick extractions
    ):
        pass
```

---

### 4.7 Content Processing Pipeline

```
Raw HTML/Markdown
        │
        ▼
┌───────────────────┐
│   ContentCleaner  │ Remove boilerplate, ads, navigation
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   SmartChunker    │ Semantic chunking (respect paragraphs)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  FactExtractor    │ Extract key facts with source attribution
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  QualityScorer    │ Score chunks by relevance, freshness, authority
└─────────┬─────────┘
          │
          ▼
    Processed Chunks
```

#### Chunking Strategy

```python
class SmartChunker:
    """
    Semantic-aware chunking that respects document structure.
    
    Strategy:
    1. Split by semantic boundaries (headers, paragraphs)
    2. Merge small chunks to meet minimum size
    3. Split large chunks at sentence boundaries
    4. Maintain overlap for context continuity
    """
    
    def __init__(
        self,
        chunk_size: int = 512,       # Target tokens
        chunk_overlap: int = 64,      # Overlap tokens
        min_chunk_size: int = 100,    # Minimum tokens
    ):
        pass
    
    def chunk(self, text: str, metadata: dict) -> List[ContentChunk]:
        pass
```

---

### 4.8 Quality Scoring

Sources are scored to prioritize high-quality content:

```python
class QualityScorer:
    """
    Multi-factor quality scoring for sources and chunks.
    """
    
    DOMAIN_AUTHORITY = {
        "edu": 0.9,
        "gov": 0.9,
        "org": 0.7,
        "com": 0.5,
        # Known high-quality domains
        "arxiv.org": 0.95,
        "nature.com": 0.95,
        "github.com": 0.8,
        ...
    }
    
    def score(self, source: Source, chunk: ContentChunk) -> float:
        """
        Factors:
        - Domain authority (0.3 weight)
        - Content freshness (0.2 weight)
        - Relevance to query (0.3 weight)
        - Content density (0.1 weight)
        - Link count/references (0.1 weight)
        """
        pass
```

---

## 5. API Specification

### 5.1 Endpoints

#### POST /api/v1/research

Start a new research session.

```json
// Request
{
  "query": "What are the latest breakthroughs in quantum computing?",
  "focus_mode": "general",  // general, academic, news, code
  "max_sources": 5,
  "stream": true,
  "session_id": null  // null for new session
}

// Response (non-streaming)
{
  "session_id": "sess_abc123",
  "answer": "Quantum computing has seen significant...[1]...[2]",
  "sources": [
    {
      "index": 1,
      "title": "Quantum Computing Advances",
      "url": "https://...",
      "domain": "nature.com",
      "snippet": "...",
      "favicon": "https://..."
    }
  ],
  "related_questions": [
    "How do quantum computers work?",
    "What companies are leading in quantum computing?"
  ],
  "metadata": {
    "tokens_used": 2340,
    "time_elapsed": 12.5,
    "sources_crawled": 5,
    "iteration_count": 1
  }
}
```

#### GET /api/v1/research/stream

SSE endpoint for streaming research.

```
event: status
data: {"message": "Planning research strategy..."}

event: status
data: {"message": "Searching for information..."}

event: sources
data: [{"index": 1, "title": "...", "url": "...", ...}]

event: token
data: {"text": "Quantum"}

event: token
data: {"text": " computing"}

event: citation
data: {"index": 1, "position": 45}

event: related
data: ["Question 1", "Question 2"]

event: done
data: {"session_id": "...", "metadata": {...}}
```

#### GET /api/v1/sources/{session_id}

Get all sources for a session.

#### POST /api/v1/session/{session_id}/followup

Continue conversation with follow-up question.

---

## 6. Configuration Management

```yaml
# config/default.yaml

app:
  name: "Diogenes"
  version: "2.0.0"
  debug: false
  log_level: "INFO"

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:3000"]

search:
  provider: "searxng"
  base_url: "http://localhost:8080"
  timeout: 20.0
  max_results: 10
  cache_ttl: 3600  # 1 hour

crawl:
  provider: "crawl4ai"
  max_concurrent: 5
  timeout: 30.0
  max_content_length: 500000  # 500KB
  rate_limit_per_domain: 2.0  # seconds between requests
  cache_ttl: 86400  # 24 hours

llm:
  provider: "ollama"
  base_url: "http://localhost:11434"
  models:
    planner: "qwen2.5:3b"       # Fast, for query decomposition
    extractor: "qwen2.5:3b"     # Fast, for fact extraction
    synthesizer: "llama3.1:8b"  # Quality, for final answer
    reflector: "llama3.1:8b"    # Quality, for reflection
  temperature: 0.0
  max_tokens: 4096
  timeout: 120.0

processing:
  chunk_size: 512
  chunk_overlap: 64
  max_chunks_per_source: 20
  max_total_context: 32000  # tokens

cache:
  provider: "sqlite"  # sqlite, redis
  database: "cache.db"
  
session:
  provider: "sqlite"
  database: "sessions.db"
  ttl: 86400  # 24 hours

agent:
  max_iterations: 3
  min_sources: 3
  coverage_threshold: 0.7
```

---

## 7. Error Handling Strategy

```python
class DiogenesError(Exception):
    """Base exception for all Diogenes errors"""
    pass

class SearchError(DiogenesError):
    """Search provider errors"""
    pass

class CrawlError(DiogenesError):
    """Crawling errors"""
    pass

class LLMError(DiogenesError):
    """LLM inference errors"""
    pass

class ConfigError(DiogenesError):
    """Configuration errors"""
    pass

# Retry Strategy
RETRY_CONFIG = {
    "search": {
        "max_attempts": 3,
        "backoff_factor": 2,
        "exceptions": [SearchError, httpx.TimeoutException]
    },
    "crawl": {
        "max_attempts": 2,
        "backoff_factor": 1,
        "exceptions": [CrawlError]
    },
    "llm": {
        "max_attempts": 2,
        "backoff_factor": 3,
        "exceptions": [LLMError]
    }
}
```

---

## 8. Performance Optimizations

### 8.1 Caching Strategy

| Cache Type | TTL | Key Format | Storage |
|------------|-----|------------|---------|
| Search results | 1 hour | `search:{hash(query)}` | SQLite |
| Crawled pages | 24 hours | `crawl:{hash(url)}` | SQLite |
| Embeddings | 7 days | `embed:{hash(text)}` | SQLite |
| LLM responses | None | Not cached (dynamic) | - |

### 8.2 Parallelization

```python
# Parallel search queries
async def search_parallel(queries: List[str]) -> List[SearchResult]:
    tasks = [search_service.search(q) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return flatten([r for r in results if not isinstance(r, Exception)])

# Parallel crawling with rate limiting
async def crawl_parallel(urls: List[str], max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)
    async with semaphore:
        # Rate limit per domain
        pass
```

### 8.3 Memory Management

```python
# Stream large content instead of loading all at once
async def process_large_content(content_stream: AsyncGenerator):
    async for chunk in content_stream:
        yield process_chunk(chunk)

# Limit context window usage
def truncate_context(chunks: List[Chunk], max_tokens: int) -> List[Chunk]:
    """Select highest-quality chunks within token budget"""
    sorted_chunks = sorted(chunks, key=lambda c: c.quality_score, reverse=True)
    selected = []
    token_count = 0
    for chunk in sorted_chunks:
        if token_count + chunk.token_count > max_tokens:
            break
        selected.append(chunk)
        token_count += chunk.token_count
    return selected
```

---

## 9. Testing Strategy

### 9.1 Test Categories

| Type | Coverage Target | Description |
|------|-----------------|-------------|
| Unit | 80% | Individual components (chunker, extractor, etc.) |
| Integration | 70% | Service interactions (search, crawl, LLM) |
| E2E | Key flows | Full research pipeline |
| Load | N/A | Concurrent user simulation |

### 9.2 Mocking External Services

```python
# tests/conftest.py

@pytest.fixture
def mock_searxng():
    """Mock SearXNG responses"""
    with respx.mock:
        respx.get("http://localhost:8080/search").respond(
            json={"results": [...]}
        )
        yield

@pytest.fixture
def mock_ollama():
    """Mock Ollama responses"""
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").respond(
            json={"response": "..."}
        )
        yield
```

---

## 10. Deployment Architecture

### 10.1 Docker Compose (Development/Single Machine)

```yaml
version: '3.8'

services:
  diogenes:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CONFIG_PATH=/app/config/development.yaml
    depends_on:
      - searxng
      - ollama
    volumes:
      - ./data:/app/data

  searxng:
    image: searxng/searxng:latest
    ports:
      - "8080:8080"
    volumes:
      - ./searxng:/etc/searxng

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

volumes:
  ollama_data:
```

---

## 11. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [x] Project restructure with new directory layout
- [ ] Configuration management (Pydantic Settings)
- [ ] Logging and error handling framework
- [ ] Abstract interfaces for all services

### Phase 2: Services (Week 2)
- [ ] SearXNG service with caching
- [ ] crawl4ai service with rate limiting
- [ ] Ollama service with streaming
- [ ] Content processing pipeline

### Phase 3: Agent (Week 3)
- [ ] LangGraph state machine
- [ ] Query planning node
- [ ] Search and crawl nodes
- [ ] Reflection and synthesis nodes

### Phase 4: Citation System (Week 4)
- [ ] Citation tracking during synthesis
- [ ] Source quality scoring
- [ ] Citation formatting

### Phase 5: API Layer (Week 5)
- [ ] FastAPI routes
- [ ] SSE streaming
- [ ] Session management

### Phase 6: Testing & Polish (Week 6)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Documentation

---

## 12. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Query-to-first-token | < 3s | P95 latency |
| Full response time | < 30s | P95 latency |
| Answer quality | > 4/5 | Human evaluation |
| Citation accuracy | > 90% | Automated + manual |
| System uptime | > 99% | Monitoring |
| Error rate | < 5% | Error logs |

---

## Appendix A: Technology Decisions Rationale

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| Agent Framework | LangChain, LangGraph, Custom | LangGraph | Native streaming, state machines, checkpointing |
| Web Framework | FastAPI, Flask, Starlette | FastAPI | Async native, Pydantic integration, SSE support |
| Cache | Redis, SQLite, In-memory | SQLite | No extra infrastructure, persistent, good enough for local |
| Config | dotenv, Pydantic Settings, YAML | Pydantic Settings + YAML | Type safety, validation, hierarchical configs |

---

*Document Version: 2.0*  
*Last Updated: January 25, 2026*
