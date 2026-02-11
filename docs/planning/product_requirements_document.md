# Product Requirement Document (PRD): Private AI Research Assistant

## 1. Introduction
This document outlines the requirements for building a **Private, Open-Source, Local-First AI Research Assistant**. The system leverages advanced **Retrieval-Augmented Generation (RAG)** and **Knowledge Graph** capabilities to provide deep insights while maintaining strict user privacy. It integrates best-in-class open-source tools including **SearXNG**, **crawl4ai**, and **Ollama**.

## 2. Goals & Objectives
*   **Privacy First:** Ensure all data processing and LLM inference happen locally or within a self-hosted environment.
*   **Deep Research:** Go beyond simple search summaries by crawling deep links and synthesizing information.
*   **Knowledge Structuring:** Build a traversable Knowledge Graph (GraphRAG) to connect disparate pieces of information.
*   **Open Source:** Foster community contribution and transparency.
*   **Local Performance:** Optimize for consumer-grade hardware using quantized models and efficient vector/graph stores.

## 3. Target Audience
*   **Researchers & Analysts:** Requiring deep, unbiased, and private synthesis of topics.
*   **Developers:** Wanting a hackable, extensible research platform.
*   **Privacy Advocates:** Users who do not want their queries and data shared with big tech providers.

## 4. Functional Requirements

### 4.1. Search & Data Acquisition
*   **Metasearch Engine:** Integrate **SearXNG** to aggregate results from multiple search engines (Google, Bing, DuckDuckGo, etc.) without tracking.
*   **Intelligent Crawling:** Use **crawl4ai** (based on Playwright) to fully render and scrape content from dynamic websites found in search results.
*   **Source Verification:** Automatically verify sources and provide citations for all claims.

### 4.2. Data Processing & Knowledge Graph
*   **Content Chunking:** Smartly chunk scraped content for vector embedding.
*   **Entity Extraction:** Use local LLMs to extract entities (people, places, concepts) and relationships.
*   **Graph Construction:** Store entities and relationships in a Graph Database (**Neo4j** or **Memgraph**) to enable multi-hop reasoning.
*   **Vector Indexing:** Store semantic embeddings in a Vector Database (**Chroma**, **Milvus**, or **FAISS**) for similarity search.

### 4.3. Interface & Interaction
*   **Chat Interface:** A conversational UI where users can ask complex questions.
*   **Graph Visualization:** Visual exploration tool to view the knowledge graph and connections.
*   **Research Reports:** Ability to generate comprehensive markdown reports (like this document's source) on a given topic.

### 4.4. LLM Integration
*   **Local Inference:** Use **Ollama** (via `llama.cpp`) to run models like Llama 3, Mistral, or specialized research models.
*   **Model Management:** Easy switching and downloading of different models via the UI/CLI.

## 5. Non-Functional Requirements
*   **Privacy:** No telemetry or data egress to third-party AI providers by default.
*   **Deployment:** Fully containerized using **Docker** and **Docker Compose** for one-click setup.
*   **Performance:**
    *   Support GPU acceleration (CUDA/Metal).
    *   Efficient memory usage for graph operations.
*   **Scalability:** Modular architecture allowing the replacement of components (e.g., swapping Vector DBs).

## 6. Technology Stack (Confirmed)
Based on the Technical Research Report (2026-01-21):

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python, C++ | Python for orchestration, C++ for high-perf inference. |
| **Local LLM** | **Ollama** | Easy management, GGUF support, API compatibility. |
| **Crawling** | **crawl4ai** | Headless browsing, async support for dynamic sites. |
| **Metasearch** | **SearXNG** | Privacy-focused, aggregate search, self-hostable. |
| **RAG Framework** | **LangChain** / **LlamaIndex** | Standard for building RAG pipelines; supports GraphRAG. |
| **Graph DB** | **Neo4j** / **Memgraph** | Robust property graph storage for knowledge mapping. |
| **Vector DB** | **Chroma** / **Milvus** | Efficient semantic similarity search. |
| **Infra** | **Docker** | Reproducible deployment. |

## 7. MVP Scope (Phase 1)
1.  **CLI Tool:** Accepts a research topic.
2.  **Pipeline:**
    *   Query SearXNG for top 10 results.
    *   Crawl the top 5 relevant URLs using crawl4ai.
    *   Summarize content using Ollama (Llama 3 8B).
3.  **Output:** Generate a markdown report with citations.
4.  **Storage:** Ephemeral or local file-based storage (SQLite/Chroma) before moving to full Graph DB.

## 8. Future Roadmap
*   **Phase 2:** Web UI and persistent Knowledge Graph (Neo4j).
*   **Phase 3:** Multi-agent system where "Researcher", "Reviewer", and "Writer" agents collaborate.
*   **Phase 4:** Collaborative features for teams (self-hosted cloud).
