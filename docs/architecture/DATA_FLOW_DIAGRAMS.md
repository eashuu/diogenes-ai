# Diogenes Data Flow Diagrams

## 1. Complete Research Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant API as FastAPI
    participant Agent as ResearchAgent
    participant Planner
    participant Search as SearXNG
    participant Crawl as crawl4ai
    participant Processor
    participant LLM as Ollama
    participant Cache
    
    User->>API: POST /research {query}
    API->>Agent: start_research(query)
    
    rect rgb(240, 248, 255)
        Note over Agent: PLAN Phase
        Agent->>Planner: decompose(query)
        Planner->>LLM: generate_subqueries(query)
        LLM-->>Planner: [subquery1, subquery2, ...]
        Planner-->>Agent: SearchPlan
    end
    
    rect rgb(255, 248, 240)
        Note over Agent: SEARCH Phase
        loop For each subquery
            Agent->>Cache: check_cache(subquery)
            alt Cache Hit
                Cache-->>Agent: cached_results
            else Cache Miss
                Agent->>Search: search(subquery)
                Search-->>Agent: SearchResults
                Agent->>Cache: store(subquery, results)
            end
        end
        Agent->>Agent: deduplicate_and_rank()
        Agent->>Agent: select_top_urls(5)
    end
    
    rect rgb(240, 255, 240)
        Note over Agent: CRAWL Phase
        Agent->>Crawl: crawl_parallel(urls)
        par Parallel Crawling
            Crawl->>Crawl: fetch(url1)
            Crawl->>Crawl: fetch(url2)
            Crawl->>Crawl: fetch(url3)
        end
        Crawl-->>Agent: CrawlResults[]
    end
    
    rect rgb(255, 240, 255)
        Note over Agent: PROCESS Phase
        Agent->>Processor: process(crawl_results)
        Processor->>Processor: clean_content()
        Processor->>Processor: chunk_semantically()
        Processor->>LLM: extract_facts(chunks)
        LLM-->>Processor: ExtractedFacts[]
        Processor->>Processor: score_quality()
        Processor-->>Agent: ProcessedContent
    end
    
    rect rgb(255, 255, 240)
        Note over Agent: REFLECT Phase
        Agent->>LLM: evaluate_coverage(query, facts)
        LLM-->>Agent: CoverageReport
        alt Coverage < 70%
            Agent->>Agent: identify_gaps()
            Note over Agent: Loop back to SEARCH
        end
    end
    
    rect rgb(240, 255, 255)
        Note over Agent: SYNTHESIZE Phase
        Agent->>LLM: synthesize_stream(query, context, citations)
        loop Streaming
            LLM-->>Agent: token
            Agent-->>API: SSE: token
            API-->>User: SSE: token
        end
        Agent->>LLM: generate_related_questions()
        LLM-->>Agent: related_questions[]
    end
    
    Agent-->>API: ResearchResult
    API-->>User: SSE: done
```

## 2. Citation Tracking Flow

```mermaid
sequenceDiagram
    participant Synthesizer
    participant CitationMgr as CitationManager
    participant LLM as Ollama
    participant Output
    
    Note over Synthesizer: Building context for synthesis
    
    Synthesizer->>CitationMgr: register_sources(crawled_pages)
    CitationMgr->>CitationMgr: assign_indices([1], [2], ...)
    CitationMgr->>CitationMgr: build_source_cards()
    CitationMgr-->>Synthesizer: SourceRegistry
    
    Synthesizer->>Synthesizer: build_context_with_markers()
    Note over Synthesizer: Each chunk prefixed with [Source N]
    
    Synthesizer->>LLM: synthesize(context_with_markers)
    
    loop For each generated token
        LLM-->>Synthesizer: token
        Synthesizer->>CitationMgr: track_citation_reference(token)
        alt Token contains [N]
            CitationMgr->>CitationMgr: record_citation_position()
        end
        Synthesizer->>Output: stream_token(token)
    end
    
    Synthesizer->>CitationMgr: get_used_citations()
    CitationMgr-->>Synthesizer: UsedCitations[]
    
    Synthesizer->>Output: emit_source_cards(used_sources_only)
```

## 3. Caching Strategy Flow

```mermaid
flowchart TD
    A[Incoming Query] --> B{Check Query Cache}
    B -->|Hit| C[Return Cached Results]
    B -->|Miss| D[Execute Search]
    
    D --> E[SearXNG Query]
    E --> F{Check URL Cache}
    
    F -->|All URLs Cached| G[Load Cached Content]
    F -->|Some URLs Cached| H[Load Cached + Crawl New]
    F -->|No URLs Cached| I[Crawl All URLs]
    
    H --> J[Merge Results]
    I --> J
    G --> K[Process Content]
    J --> K
    
    K --> L[Store in Cache]
    L --> M[Return Results]
    
    subgraph Cache TTLs
        N[Search Cache: 1 hour]
        O[Crawl Cache: 24 hours]
        P[Embedding Cache: 7 days]
    end
```

## 4. Quality Scoring Pipeline

```mermaid
flowchart LR
    subgraph Input
        A[Source URL]
        B[Content Chunks]
        C[Query Context]
    end
    
    subgraph "Domain Authority (30%)"
        D[Parse Domain]
        E[Lookup Authority Score]
        F[Known Quality Domains]
    end
    
    subgraph "Freshness (20%)"
        G[Extract Date]
        H[Calculate Recency]
        I[Decay Function]
    end
    
    subgraph "Relevance (30%)"
        J[Query Embedding]
        K[Chunk Embedding]
        L[Cosine Similarity]
    end
    
    subgraph "Content Quality (20%)"
        M[Text Density]
        N[Reference Count]
        O[Readability Score]
    end
    
    A --> D --> E
    F --> E
    
    B --> G --> H --> I
    
    C --> J
    B --> K
    J --> L
    K --> L
    
    B --> M
    B --> N
    B --> O
    
    E --> P[Weighted Sum]
    I --> P
    L --> P
    M --> P
    N --> P
    O --> P
    
    P --> Q[Final Score: 0.0 - 1.0]
```

## 5. Error Recovery Flow

```mermaid
stateDiagram-v2
    [*] --> Search
    
    Search --> SearchError: Timeout/Error
    SearchError --> RetrySearch: Attempt < 3
    RetrySearch --> Search
    SearchError --> PartialResults: All retries failed
    PartialResults --> Crawl: Continue with available results
    
    Search --> Crawl: Success
    
    Crawl --> CrawlError: Page failed
    CrawlError --> SkipPage: Mark as failed
    SkipPage --> Crawl: Try next URL
    
    Crawl --> Process: Enough pages crawled
    Crawl --> SearchMore: Too few pages
    SearchMore --> Search: With new queries
    
    Process --> ProcessError: Extraction failed
    ProcessError --> SimpleProcess: Fallback to basic chunking
    SimpleProcess --> Process
    
    Process --> Synthesize: Content ready
    
    Synthesize --> LLMError: Model error
    LLMError --> RetryLLM: Attempt < 2
    RetryLLM --> Synthesize
    LLMError --> FallbackModel: Use smaller model
    FallbackModel --> Synthesize
    
    Synthesize --> [*]: Success
```

## 6. Streaming SSE Protocol

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant Agent
    
    Client->>Server: GET /research/stream?query=...
    Server->>Server: Set headers (text/event-stream)
    Server-->>Client: HTTP 200 (keep-alive)
    
    Server->>Agent: start_research()
    
    Agent-->>Server: status_update("Planning...")
    Server-->>Client: event: status\ndata: {"msg": "Planning..."}
    
    Agent-->>Server: status_update("Searching...")
    Server-->>Client: event: status\ndata: {"msg": "Searching..."}
    
    Agent-->>Server: sources_found(sources)
    Server-->>Client: event: sources\ndata: [{...}, {...}]
    
    Agent-->>Server: status_update("Synthesizing...")
    Server-->>Client: event: status\ndata: {"msg": "Synthesizing..."}
    
    loop Token Stream
        Agent-->>Server: token("word")
        Server-->>Client: event: token\ndata: {"text": "word"}
    end
    
    Agent-->>Server: related_questions([...])
    Server-->>Client: event: related\ndata: ["Q1", "Q2"]
    
    Agent-->>Server: complete(metadata)
    Server-->>Client: event: done\ndata: {...}
    
    Server-->>Client: Connection closed
```

## 7. Agent State Transitions

```mermaid
stateDiagram-v2
    [*] --> INIT
    
    INIT --> PLAN: start_research()
    
    PLAN --> SEARCH: plan_complete
    PLAN --> ERROR: plan_failed
    
    SEARCH --> CRAWL: urls_selected
    SEARCH --> REFLECT: no_results
    
    CRAWL --> PROCESS: pages_crawled
    CRAWL --> SEARCH: all_crawls_failed
    
    PROCESS --> REFLECT: content_processed
    PROCESS --> ERROR: processing_failed
    
    REFLECT --> SYNTHESIZE: coverage_sufficient
    REFLECT --> SEARCH: need_more_info
    REFLECT --> SYNTHESIZE: max_iterations_reached
    
    SYNTHESIZE --> COMPLETE: synthesis_done
    SYNTHESIZE --> ERROR: synthesis_failed
    
    COMPLETE --> [*]
    ERROR --> [*]
    
    note right of REFLECT
        Decides if we have enough
        information or need to
        search for more
    end note
```

## 8. Parallel Processing Architecture

```mermaid
flowchart TB
    subgraph "Query Decomposition"
        Q[User Query] --> D[Decompose]
        D --> Q1[SubQuery 1]
        D --> Q2[SubQuery 2]
        D --> Q3[SubQuery 3]
    end
    
    subgraph "Parallel Search"
        Q1 --> S1[Search 1]
        Q2 --> S2[Search 2]
        Q3 --> S3[Search 3]
        S1 --> M[Merge & Dedupe]
        S2 --> M
        S3 --> M
    end
    
    subgraph "URL Selection"
        M --> R[Rank by Relevance]
        R --> U1[URL 1]
        R --> U2[URL 2]
        R --> U3[URL 3]
        R --> U4[URL 4]
        R --> U5[URL 5]
    end
    
    subgraph "Parallel Crawling"
        U1 --> C1[Crawl 1]
        U2 --> C2[Crawl 2]
        U3 --> C3[Crawl 3]
        U4 --> C4[Crawl 4]
        U5 --> C5[Crawl 5]
    end
    
    subgraph "Parallel Processing"
        C1 --> P1[Process 1]
        C2 --> P2[Process 2]
        C3 --> P3[Process 3]
        C4 --> P4[Process 4]
        C5 --> P5[Process 5]
    end
    
    subgraph "Synthesis"
        P1 --> A[Aggregate]
        P2 --> A
        P3 --> A
        P4 --> A
        P5 --> A
        A --> SYN[Synthesize with LLM]
    end
```
