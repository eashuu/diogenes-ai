"""
Researcher Agent.

Specialized agent for gathering information from various sources:
- Web search (SearXNG, etc.)
- Academic sources (ArXiv, Semantic Scholar)
- Code repositories (GitHub)
- Web crawling and content extraction
"""

import asyncio
from typing import Any, Optional
from dataclasses import dataclass

from src.utils.logging import get_logger
from src.utils.exceptions import SearchError, CrawlError
from src.core.agents.base import BaseAgent, AgentCapability
from src.core.agents.protocol import (
    TaskAssignment,
    TaskResult,
    TaskType,
)
from src.services.search.searxng import SearXNGService
from src.services.crawl.crawler import Crawl4AIService
from src.processing.cleaner import ContentCleaner
from src.processing.chunker import SmartChunker
from src.processing.scorer import QualityScorer
from src.config import get_settings


logger = get_logger(__name__)


class ResearcherAgent(BaseAgent):
    """
    Agent specialized in gathering information from various sources.
    
    Capabilities:
    - Web search (multiple engines via SearXNG)
    - Academic paper search (ArXiv, Semantic Scholar)
    - Code repository search (GitHub, StackOverflow)
    - Web crawling with content extraction
    - Document loading (PDF, DOCX, etc.)
    """
    
    def __init__(
        self,
        search_service: Optional[SearXNGService] = None,
        crawl_service: Optional[Crawl4AIService] = None,
    ):
        """
        Initialize the researcher agent.
        
        Args:
            search_service: Search service instance
            crawl_service: Crawl service instance
        """
        super().__init__(
            agent_type="researcher",
            capabilities=[
                AgentCapability.SEARCHING,
                AgentCapability.CRAWLING,
                AgentCapability.PROCESSING
            ]
        )
        
        self._search_service = search_service
        self._crawl_service = crawl_service
        self._cleaner = None
        self._chunker = None
        self._scorer = None
        self._settings = None
    
    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings
    
    @property
    def search_service(self) -> SearXNGService:
        """Lazy load search service."""
        if self._search_service is None:
            self._search_service = SearXNGService(
                base_url=self.settings.search.base_url,
                timeout=self.settings.search.timeout,
                max_results=self.settings.search.max_results
            )
        return self._search_service
    
    @property
    def crawl_service(self) -> Crawl4AIService:
        """Lazy load crawl service."""
        if self._crawl_service is None:
            self._crawl_service = Crawl4AIService(
                max_concurrent=self.settings.crawl.max_concurrent,
                default_timeout=self.settings.crawl.timeout,
                max_content_length=self.settings.crawl.max_content_length,
                rate_limit=self.settings.crawl.rate_limit_per_domain
            )
        return self._crawl_service
    
    @property
    def cleaner(self) -> ContentCleaner:
        """Lazy load content cleaner."""
        if self._cleaner is None:
            self._cleaner = ContentCleaner()
        return self._cleaner
    
    @property
    def chunker(self) -> SmartChunker:
        """Lazy load chunker."""
        if self._chunker is None:
            self._chunker = SmartChunker(
                chunk_size=self.settings.processing.chunk_size,
                chunk_overlap=self.settings.processing.chunk_overlap,
                min_chunk_size=self.settings.processing.min_chunk_size
            )
        return self._chunker
    
    @property
    def scorer(self) -> QualityScorer:
        """Lazy load quality scorer."""
        if self._scorer is None:
            self._scorer = QualityScorer()
        return self._scorer
    
    async def execute(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a research task.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result with gathered information
        """
        task_type = task.task_type
        
        if task_type == TaskType.WEB_SEARCH:
            return await self._web_search(task)
        elif task_type == TaskType.ACADEMIC_SEARCH:
            return await self._academic_search(task)
        elif task_type == TaskType.CODE_SEARCH:
            return await self._code_search(task)
        elif task_type == TaskType.CRAWL_URLS:
            return await self._crawl_urls(task)
        elif task_type == TaskType.LOAD_DOCUMENTS:
            return await self._load_documents(task)
        else:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[f"Unknown task type for researcher: {task_type}"]
            )
    
    async def _web_search(self, task: TaskAssignment) -> TaskResult:
        """
        Execute web search across multiple queries.
        
        Args:
            task: Task with search queries
            
        Returns:
            Search results
        """
        queries = task.inputs.get("queries", [])
        if isinstance(queries, str):
            queries = [queries]
        
        num_results = task.inputs.get("num_results", 10)
        
        logger.info(f"Executing web search with {len(queries)} queries")
        
        all_results = []
        seen_urls = set()
        errors = []
        
        try:
            # Execute searches in parallel
            search_tasks = [
                self.search_service.search(query=q, num_results=num_results)
                for q in queries
            ]
            
            responses = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            for query, response in zip(queries, responses):
                if isinstance(response, Exception):
                    logger.warning(f"Search failed for '{query}': {response}")
                    errors.append(str(response))
                    continue
                
                # Deduplicate by URL
                for result in response.results:
                    if result.url not in seen_urls:
                        seen_urls.add(result.url)
                        all_results.append({
                            "url": result.url,
                            "title": result.title,
                            "snippet": result.snippet,
                            "score": result.score,
                            "engine": result.engine,
                            "query": query
                        })
            
            # Sort by score
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            logger.info(f"Found {len(all_results)} unique results")
            
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success" if all_results else "partial",
                outputs={
                    "results": all_results,
                    "total_found": len(all_results),
                    "queries_executed": len(queries),
                    "queries_failed": len(errors)
                },
                confidence=0.9 if all_results else 0.3,
                errors=errors
            )
            
        except SearchError as e:
            logger.error(f"Search error: {e}")
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)]
            )
    
    async def _academic_search(self, task: TaskAssignment) -> TaskResult:
        """
        Search academic sources via ArXiv API + web-search fallback.

        Uses the native ``ArxivService`` for direct API queries, then
        supplements with a SearXNG web search scoped to scholarly domains.
        """
        from src.services.search.arxiv import ArxivService

        queries = task.inputs.get("queries", [])
        if isinstance(queries, str):
            queries = [queries]

        max_results = task.inputs.get("max_results", 5)
        all_results: list[dict] = []

        # --- ArXiv direct API search ----------------------------------------
        try:
            arxiv = ArxivService()
            for q in queries:
                try:
                    search_result = await arxiv.search(query=q, max_results=max_results)
                    for paper in search_result.papers:
                        all_results.append({
                            "title": paper.title,
                            "url": paper.abs_url,
                            "pdf_url": paper.pdf_url,
                            "snippet": paper.summary[:500],
                            "domain": "arxiv.org",
                            "source": "arxiv_api",
                            "quality_score": 0.9,   # academic papers are high quality
                            "metadata": {
                                "arxiv_id": paper.arxiv_id,
                                "authors": [a.name for a in paper.authors],
                                "categories": paper.categories,
                                "published": paper.published.isoformat(),
                            },
                        })
                except Exception as e:
                    logger.warning(f"ArXiv API search failed for '{q}': {e}")
            await arxiv.close()
        except Exception as e:
            logger.warning(f"ArXiv service init failed: {e}")

        # --- Web search fallback (scholarly domains) -------------------------
        academic_queries = [
            f"{q} site:scholar.google.com OR site:pubmed.gov OR site:semanticscholar.org"
            for q in queries
        ]
        modified_task = TaskAssignment(
            task_type=task.task_type,
            agent_type=task.agent_type,
            inputs={**task.inputs, "queries": academic_queries},
            task_id=task.task_id,
            constraints=task.constraints,
            dependencies=task.dependencies,
            priority=task.priority,
            timeout=task.timeout,
            is_critical=task.is_critical,
        )
        web_result = await self._web_search(modified_task)

        # Merge web results with ArXiv results (dedup by URL)
        seen_urls = {r["url"] for r in all_results}
        web_sources = web_result.outputs.get("results", [])
        for src in web_sources:
            url = src.get("url", "")
            if url and url not in seen_urls:
                all_results.append(src)
                seen_urls.add(url)

        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="success",
            outputs={"results": all_results, "result_count": len(all_results)},
            confidence=0.85 if all_results else 0.3,
        )
    
    async def _code_search(self, task: TaskAssignment) -> TaskResult:
        """
        Search code repositories.
        
        TODO: Implement GitHub API integration.
        For now, this uses web search with code domains.
        """
        queries = task.inputs.get("queries", [])
        if isinstance(queries, str):
            queries = [queries]
        
        # Enhance queries for code search
        code_queries = [
            f"{q} site:github.com OR site:stackoverflow.com OR site:docs.python.org"
            for q in queries
        ]
        
        # Reuse web search with a modified copy of inputs (avoid mutating original task)
        modified_task = TaskAssignment(
            task_type=task.task_type,
            agent_type=task.agent_type,
            inputs={**task.inputs, "queries": code_queries},
            task_id=task.task_id,
            constraints=task.constraints,
            dependencies=task.dependencies,
            priority=task.priority,
            timeout=task.timeout,
            is_critical=task.is_critical,
        )
        return await self._web_search(modified_task)
    
    async def _crawl_urls(self, task: TaskAssignment) -> TaskResult:
        """
        Crawl URLs and extract content.
        
        Args:
            task: Task with URLs to crawl
            
        Returns:
            Crawled content
        """
        urls = task.inputs.get("urls", [])
        timeout = task.inputs.get("timeout", 30.0)
        
        if not urls:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                outputs={"results": [], "crawled": 0, "failed": 0}
            )
        
        logger.info(f"Crawling {len(urls)} URLs")
        
        try:
            # Batch crawl
            batch_result = await self.crawl_service.crawl_many(urls)
            
            processed_results = []
            failures = []
            
            def _process_crawl_results():
                """CPU-bound content processing — runs in executor."""
                _processed = []
                _failed = []
                for result in batch_result.results:
                    if result.is_success:
                        # Clean content
                        cleaned = self.cleaner.clean(result.content or "")
                        
                        # Score quality using score_source method with CrawlResult
                        quality_score = self.scorer.score_source(result)
                        
                        # Chunk content with source info
                        chunks = self.chunker.chunk(
                            content=cleaned,
                            source_url=result.url,
                            source_title=result.title or ""
                        )
                        
                        _processed.append({
                            "url": result.url,
                            "title": result.title,
                            "content": cleaned,
                            "chunks": [c.content for c in chunks],
                            "quality_score": quality_score,
                            "content_length": len(cleaned),
                            "chunk_count": len(chunks)
                        })
                    else:
                        _failed.append({
                            "url": result.url,
                            "error": result.error_message
                        })
                return _processed, _failed
            
            # Run CPU-bound processing off the event loop
            loop = asyncio.get_event_loop()
            processed_results, failures = await loop.run_in_executor(
                None, _process_crawl_results
            )
            
            logger.info(
                f"Crawled {len(processed_results)} pages, "
                f"{len(failures)} failures"
            )
            
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success" if processed_results else "partial",
                outputs={
                    "results": processed_results,
                    "failures": failures,
                    "crawled": len(processed_results),
                    "failed": len(failures)
                },
                confidence=len(processed_results) / max(len(urls), 1),
                errors=[f["error"] for f in failures]
            )
            
        except CrawlError as e:
            logger.error(f"Crawl error: {e}")
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)]
            )
    
    async def _load_documents(self, task: TaskAssignment) -> TaskResult:
        """
        Load and process documents (PDF, etc.) from file paths or URLs.

        Supports:
        - Local PDF files via file_paths
        - Remote PDF URLs via pdf_urls

        Uses ``PDFLoader`` (pypdf backend by default) to extract text,
        then runs the same clean→chunk→score pipeline as crawled content.
        """
        from src.services.crawl.pdf_loader import PDFLoader

        file_paths: list[str] = task.inputs.get("file_paths", [])
        pdf_urls: list[str] = task.inputs.get("pdf_urls", [])

        if not file_paths and not pdf_urls:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="partial",
                outputs={"documents": [], "message": "No file_paths or pdf_urls provided"},
                errors=["No document sources provided"],
            )

        loader = PDFLoader(backend="pypdf")

        documents: list[dict] = []
        errors: list[str] = []

        # Load local files
        for path in file_paths:
            try:
                doc = await loader.load_file(path)
                processed = self._process_pdf_document(doc)
                documents.append(processed)
                logger.info(f"Loaded PDF file: {path} ({doc.total_words} words)")
            except FileNotFoundError:
                errors.append(f"File not found: {path}")
                logger.warning(f"PDF file not found: {path}")
            except ImportError as e:
                errors.append(f"PDF backend not installed: {e}")
                logger.error(f"PDF backend error: {e}")
                break  # No point trying more files
            except Exception as e:
                errors.append(f"Failed to load {path}: {e}")
                logger.warning(f"Failed to load PDF {path}: {e}")

        # Load remote PDFs
        for url in pdf_urls:
            try:
                doc = await loader.load_url(url)
                processed = self._process_pdf_document(doc)
                documents.append(processed)
                logger.info(f"Loaded PDF URL: {url} ({doc.total_words} words)")
            except Exception as e:
                errors.append(f"Failed to load {url}: {e}")
                logger.warning(f"Failed to load PDF URL {url}: {e}")

        # Clean up loader HTTP client
        if loader._client and not loader._client.is_closed:
            await loader._client.aclose()

        status = "success" if documents and not errors else "partial" if documents else "failed"

        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status=status,
            outputs={
                "documents": documents,
                "loaded": len(documents),
                "failed": len(errors),
            },
            confidence=len(documents) / max(len(file_paths) + len(pdf_urls), 1),
            errors=errors,
        )

    def _process_pdf_document(self, doc) -> dict:
        """Process a PDFDocument through clean→chunk→score pipeline."""
        import asyncio

        # Clean the extracted text
        cleaned = self.cleaner.clean(doc.full_text)

        # Chunk the cleaned text
        chunks = self.chunker.chunk(cleaned)

        # Score chunks
        scored_chunks = []
        for chunk in chunks:
            score = self.scorer.score(chunk)
            scored_chunks.append({
                "text": chunk,
                "score": score,
            })

        return {
            "source": doc.source,
            "title": doc.metadata.title or doc.source,
            "content": cleaned,
            "chunks": scored_chunks,
            "metadata": doc.to_dict(),
            "word_count": doc.total_words,
            "page_count": len(doc.pages),
        }
    
    async def search_and_crawl(
        self,
        queries: list[str],
        num_results: int = 10,
        max_crawl: int = 15
    ) -> tuple[list[dict], list[dict]]:
        """
        Convenience method to search and crawl in one call.
        
        Args:
            queries: Search queries
            num_results: Results per query
            max_crawl: Maximum URLs to crawl
            
        Returns:
            Tuple of (search_results, crawl_results)
        """
        # Search
        search_task = TaskAssignment(
            task_type=TaskType.WEB_SEARCH,
            agent_type="researcher",
            inputs={"queries": queries, "num_results": num_results}
        )
        search_result = await self.execute(search_task)
        
        if not search_result.is_success and not search_result.is_partial:
            return [], []
        
        search_results = search_result.outputs.get("results", [])
        
        # Get URLs to crawl
        urls = [r["url"] for r in search_results[:max_crawl]]
        
        # Crawl
        crawl_task = TaskAssignment(
            task_type=TaskType.CRAWL_URLS,
            agent_type="researcher",
            inputs={"urls": urls}
        )
        crawl_result = await self.execute(crawl_task)
        
        crawl_results = crawl_result.outputs.get("results", [])
        
        return search_results, crawl_results
