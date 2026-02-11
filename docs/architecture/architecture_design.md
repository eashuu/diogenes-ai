# Architecture & Data Flow Design: Private AI Research Assistant

## 1. System Overview
This project builds a **Local-First, Privacy-Preserving Research Assistant** that synthesizes information from the web. Unlike a standard RAG system that retrieves pre-indexed data, this system performs **Just-In-Time (JIT) Research**: it searches, reads, organizes, and learns from the web in real-time to answer complex queries.

The architecture follows a pipeline pattern: **Query -> Search -> Crawl -> Process -> Graph/Vector Store -> Synthesize**.

## 2. High-Level Architecture Diagram
```mermaid
graph TD
    User[User] -->|Query| UI[Web UI / CLI]
    UI -->|Request| Orchestrator[Orchestrator (Python/LangGraph)]
    
    subgraph "External Retrieval"
        Orchestrator -->|1. Search Queries| SearXNG[SearXNG (Metasearch)]
        SearXNG -->|Results (JSON)| Orchestrator
        Orchestrator -->|2. URLs| Crawler[crawl4ai (Headless Browser)]
        Crawler -->|Raw HTML/Text| Orchestrator
    end
    
    subgraph "Local Intelligence (Ollama)"
        Orchestrator -->|3. Prompts| LLM[Local LLM (Llama 3 / Mistral)]
        LLM -->|Analysis/Extraction| Orchestrator
    end
    
    subgraph "Knowledge Engine"
        Orchestrator -->|4. Store Chunks| VectorDB[(Vector DB\nChroma/Milvus)]
        Orchestrator -->|5. Store Entities| GraphDB[(Graph DB\nNeo4j/Memgraph)]
        VectorDB -->|Context| Orchestrator
        GraphDB -->|Context| Orchestrator
    end
    
    Orchestrator -->|6. Final Answer| UI
```

## 3. Component Details & Technology Stack

### A. The Orchestrator (Brain)
*   **Technology:** Python, LangGraph (or LangChain).
*   **Role:** Manages the state of the research session. It decides "Do I have enough info?" or "Do I need to search more?".
*   **Key Logic:**
    *   **Query Decomposition:** Breaks "Who are the key players in AI and what are their stances?" into sub-queries.
    *   **Tool Calling:** Decides when to call SearXNG vs. Crawler.

### B. Search Layer (The Eyes - Wide)
*   **Technology:** SearXNG.
*   **Role:** Finds *where* information lives.
*   **Configuration:** Returns JSON; Aggregates Google, Bing, DDG; No tracking.

### C. Crawl Layer (The Eyes - Deep)
*   **Technology:** crawl4ai (Playwright).
*   **Role:** Reads the actual content.
*   **Capabilities:**
    *   Bypasses simple bot detection (User-Agent rotation).
    *   Executes JS to get dynamic content.
    *   Extracts main content (readable text) vs. boilerplate (navbars/ads).

### D. Processing & Memory Layer (The Cortex)
This is where raw text becomes structured knowledge.
1.  **Vector Store (Semantic Memory):**
    *   **Tech:** Chroma or Milvus.
    *   **Role:** "Find text segments similar to X".
    *   **Flow:** Raw Text -> Chunking (recursive) -> Embedding Model (nomic-embed-text) -> Vector Index.
2.  **Knowledge Graph (Structured Memory):**
    *   **Tech:** Neo4j or Memgraph.
    *   **Role:** "How is Entity A related to Entity B?".
    *   **Flow:** Text Chunk -> LLM Extraction ("Extract entities & relations") -> Graph Upsert.

### E. Inference Layer (The Voice)
*   **Technology:** Ollama.
*   **Models:**
    *   **Orchestration/Synthesis:** Llama 3 (8B) or Mistral 7B (good reasoning).
    *   **Extraction:** Specialized extraction models (or prompted Llama 3).
    *   **Embeddings:** `nomic-embed-text-v1.5` (running in Ollama or locally via sentence-transformers).

## 4. End-to-End Data Flow (Top to Bottom)

Here is the step-by-step lifecycle of a user request:

### Step 1: Intent Understanding
*   **User** types: *"What are the latest breakthroughs in solid-state batteries?"*
*   **Orchestrator** sends this to **LLM**.
*   **LLM** generates a research plan:
    *   *Search 1: "current solid state battery breakthroughs 2024 2025"*
    *   *Search 2: "major companies solid state batteries"*

### Step 2: Discovery (SearXNG)
*   **Orchestrator** sends queries to **SearXNG API**.
*   **SearXNG** aggregates results from Google/Bing.
*   **Output:** List of 20 relevant URLs with snippets.
*   **Filter:** System filters out PDFs (optional), YouTube, or known low-quality sites. Selects Top 5 promising URLs.

### Step 3: Acquisition (crawl4ai)
*   **Orchestrator** sends Top 5 URLs to **crawl4ai**.
*   **crawl4ai** spins up headless browser -> Renders Page -> Scrapes Main Content (Markdown).
*   **Output:** 5 large blocks of markdown text.

### Step 4: Knowledge Extraction (The "GraphRAG" Magic)
*   **Orchestrator** processes each document:
    *   **Chunking:** Split text into 500-token chunks.
    *   **Vectorization:** Embed chunks -> Store in **VectorDB**.
    *   **Graph Extraction:** Send chunk to **LLM** with prompt: *"Extract entities (Companies, Technologies, KPIs) and relationships."*
    *   **Graph Construction:**
        *   *(Node: Toyota) --[working_on]--> (Node: sulfide-based electrolyte)*
        *   *(Node: QuantumScape) --[claims]--> (Node: 1000 cycles)*
    *   Store these triples in **GraphDB**.

### Step 5: Synthesis & Answer
*   **Orchestrator** constructs the "Context Window" for the final answer:
    *   **Vector Retrieval:** Query VectorDB for "breakthroughs".
    *   **Graph Retrieval:** Query GraphDB for 2-hop neighbors of "Solid State Battery".
*   **Orchestrator** sends {Original Question + Vector Context + Graph Facts} to **LLM**.
*   **LLM** generates: *"The latest breakthroughs involve sulfide-based electrolytes... Key players like Toyota and QuantumScape are..."* along with **Citations**.

## 5. File Structure & Component Mapping
```text
/diogenes
├── /searxng            # [Configured] Search Engine configuration
├── /src
│   ├── /agents         # Orchestrator logic (LangGraph)
│   ├── /tools          # Tools: SearchTool, CrawlTool
│   ├── /graph          # Neo4j/Memgraph integration
│   ├── /llm            # Ollama client wrappers
│   └── /api            # FastAPI backend (future)
├── /data               # Local persistence for Vector/Graph DBs
└── docker-compose.yml  # [Active] Container orchestration
```

## 6. Critical Implementation Details
*   **Async/Await:** Web crawling is slow. The Python code must be fully asynchronous to crawl 5 pages in parallel, not sequentially.
*   **Rate Limiting:** We must respect `robots.txt` where possible and not DDoS sites.
*   **Context Window Management:** We cannot stuff *all* scraped text into Llama 3. This is why the **Vector DB** (for semantic search) and **Graph DB** (for structural facts) are mandatory buffers.

## 7. Next Steps for Implementation
1.  **Project Structure:** Set up the Python project structure (`poetry` or `pip`).
2.  **Core Tools:** Implement `SearchTool` (wrapping our local SearXNG) and `CrawlTool` (using crawl4ai).
3.  **LLM Client:** Set up a robust Ollama Python client.
4.  **Orchestrator:** Build the "Research Loop" (Search -> Crawl -> Summarize).
