"""
LangGraph Agent Nodes.

Each node represents a step in the research process.
Nodes take the current state and return state updates.
"""

import asyncio
import json
import time
from typing import Any

from src.config import get_settings
from src.utils.logging import get_logger
from src.utils.exceptions import (
    SearchError,
    CrawlError,
    LLMError,
    ProcessingError,
    AgentError
)
from src.services.search.searxng import SearXNGService
from src.services.search.models import SearchQuery
from src.services.crawl.crawler import Crawl4AIService
from src.services.llm.ollama import OllamaService
from src.processing.cleaner import ContentCleaner
from src.processing.chunker import SmartChunker
from src.processing.scorer import QualityScorer
from src.processing.extractor import FactExtractor
from src.core.citation.manager import CitationManager
from src.core.agent.state import (
    ResearchState,
    AgentPhase,
    ResearchContext
)
from src.core.agent.prompts import (
    RESEARCH_PLANNER_SYSTEM,
    RESEARCH_PLANNER_USER,
    REFLECTION_SYSTEM,
    REFLECTION_USER,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
    SYNTHESIS_WITH_GAPS,
    FACT_EXTRACTION_SYSTEM,
    FACT_EXTRACTION_USER,
    format_sources_for_synthesis,
    format_gathered_info,
    format_gaps_list
)


logger = get_logger(__name__)


class NodeServices:
    """
    Container for services used by nodes.
    
    Lazily initializes services to avoid circular imports
    and allow for configuration-based initialization.
    """
    _instance = None
    
    def __init__(self):
        self._search_service = None
        self._crawl_service = None
        self._llm_service = None
        self._cleaner = None
        self._chunker = None
        self._scorer = None
        self._extractor = None
        self._citation_manager = None
        self._settings = None
    
    @classmethod
    def get_instance(cls) -> "NodeServices":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings
    
    @property
    def search_service(self) -> SearXNGService:
        if self._search_service is None:
            self._search_service = SearXNGService(
                base_url=self.settings.search.base_url,
                timeout=self.settings.search.timeout,
                max_results=self.settings.search.max_results
            )
        return self._search_service
    
    @property
    def crawl_service(self) -> Crawl4AIService:
        if self._crawl_service is None:
            self._crawl_service = Crawl4AIService(
                max_concurrent=self.settings.crawl.max_concurrent,
                default_timeout=self.settings.crawl.timeout,
                max_content_length=self.settings.crawl.max_content_length,
                rate_limit=self.settings.crawl.rate_limit_per_domain
            )
        return self._crawl_service
    
    @property
    def llm_service(self) -> OllamaService:
        if self._llm_service is None:
            self._llm_service = OllamaService(
                base_url=self.settings.llm.base_url,
                default_model=self.settings.llm.models.synthesizer,
                timeout=self.settings.llm.timeout
            )
        return self._llm_service
    
    @property
    def cleaner(self) -> ContentCleaner:
        if self._cleaner is None:
            self._cleaner = ContentCleaner()
        return self._cleaner
    
    @property
    def chunker(self) -> SmartChunker:
        if self._chunker is None:
            self._chunker = SmartChunker(
                chunk_size=self.settings.processing.chunk_size,
                chunk_overlap=self.settings.processing.chunk_overlap,
                min_chunk_size=self.settings.processing.min_chunk_size
            )
        return self._chunker
    
    @property
    def scorer(self) -> QualityScorer:
        if self._scorer is None:
            self._scorer = QualityScorer()
        return self._scorer
    
    @property
    def extractor(self) -> FactExtractor:
        if self._extractor is None:
            self._extractor = FactExtractor(self.llm_service)
        return self._extractor
    
    def get_citation_manager(self) -> CitationManager:
        """Get a fresh citation manager for each research session."""
        return CitationManager()


def get_services() -> NodeServices:
    """Get the services singleton."""
    return NodeServices.get_instance()


# =============================================================================
# PLANNING NODE
# =============================================================================

async def plan_node(state: ResearchState) -> dict[str, Any]:
    """
    Plan the research strategy.
    
    Takes the user query and creates:
    - Sub-queries for comprehensive coverage
    - Search strategies to use
    - Expected source types
    
    Args:
        state: Current research state
        
    Returns:
        State updates with research plan
    """
    start_time = time.time()
    services = get_services()
    
    query = state.get("query", "")
    logger.info(f"Planning research for: {query[:100]}...")
    
    try:
        # Use LLM to create research plan
        response = await services.llm_service.generate(
            prompt=RESEARCH_PLANNER_USER.format(query=query),
            system=RESEARCH_PLANNER_SYSTEM
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            plan = json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse plan JSON: {e}")
            # Fallback to simple plan
            plan = {
                "intent": query,
                "sub_queries": [query],
                "search_strategies": ["general"],
                "expected_source_types": ["web"],
                "key_concepts": []
            }
        
        elapsed = time.time() - start_time
        
        return {
            "research_plan": plan,
            "sub_queries": plan.get("sub_queries", [query]),
            "search_strategies": plan.get("search_strategies", ["general"]),
            "phase": AgentPhase.SEARCHING,
            "timing": {**state.get("timing", {}), "planning": elapsed},
            "stream_events": [{
                "type": "planning_complete",
                "data": {
                    "sub_queries": plan.get("sub_queries", []),
                    "intent": plan.get("intent", "")
                }
            }]
        }
        
    except LLMError as e:
        logger.error(f"LLM error during planning: {e}")
        # Fallback to basic plan
        return {
            "research_plan": {"intent": query},
            "sub_queries": [query],
            "search_strategies": ["general"],
            "phase": AgentPhase.SEARCHING,
            "errors": [{"phase": "planning", "error": str(e)}]
        }


# =============================================================================
# SEARCH NODE
# =============================================================================

async def search_node(state: ResearchState) -> dict[str, Any]:
    """
    Execute search queries.
    
    Runs all sub-queries and collects results.
    Handles both initial search and follow-up searches.
    
    Args:
        state: Current research state
        
    Returns:
        State updates with search results
    """
    start_time = time.time()
    services = get_services()
    
    sub_queries = state.get("sub_queries", [])
    existing_results = state.get("search_results", [])
    mode_config = state.get("mode_config")
    
    # Get search limit from mode config
    num_results = mode_config.max_search_results if mode_config else 10
    
    logger.info(f"Searching with {len(sub_queries)} queries (limit: {num_results} per query)")
    
    all_results = []
    results_by_query = dict(state.get("search_results_by_query", {}))
    errors = []
    
    try:
        # Execute all searches in parallel
        logger.info(f"Executing {len(sub_queries)} searches: {sub_queries}")
        search_tasks = [
            services.search_service.search(
                query=q,  # Pass string, not SearchQuery object
                num_results=num_results
            )
            for q in sub_queries
        ]
        
        responses = await asyncio.gather(*search_tasks, return_exceptions=True)
        logger.info(f"Received {len(responses)} search responses")
        
        seen_urls = {r.url for r in existing_results}
        
        for query, response in zip(sub_queries, responses):
            if isinstance(response, Exception):
                logger.warning(f"Search failed for '{query}': {response}")
                errors.append({
                    "phase": "search",
                    "query": query,
                    "error": str(response)
                })
                continue
            
            # Deduplicate by URL
            new_results = [
                r for r in response.results
                if r.url not in seen_urls
            ]
            
            for r in new_results:
                seen_urls.add(r.url)
            
            all_results.extend(new_results)
            results_by_query[query] = new_results
            
            logger.info(f"Found {len(new_results)} new results for: {query[:50]}")
        
        # Collect URLs to crawl (top results)
        urls_to_crawl = [r.url for r in all_results[:15]]
        
        elapsed = time.time() - start_time
        
        return {
            "search_results": all_results,
            "search_results_by_query": results_by_query,
            "urls_to_crawl": urls_to_crawl,
            "phase": AgentPhase.CRAWLING,
            "timing": {**state.get("timing", {}), "search": elapsed},
            "errors": errors if errors else [],
            "stream_events": [{
                "type": "search_complete",
                "data": {
                    "total_results": len(all_results),
                    "urls_to_crawl": len(urls_to_crawl)
                }
            }]
        }
        
    except SearchError as e:
        logger.error(f"Search error: {e}")
        return {
            "phase": AgentPhase.ERROR,
            "errors": [{"phase": "search", "error": str(e)}]
        }


# =============================================================================
# CRAWL NODE
# =============================================================================

async def crawl_node(state: ResearchState) -> dict[str, Any]:
    """
    Crawl URLs and extract content.
    
    Fetches full content from search result URLs.
    Handles failures gracefully.
    
    Args:
        state: Current research state
        
    Returns:
        State updates with crawl results
    """
    start_time = time.time()
    services = get_services()
    mode_config = state.get("mode_config")
    
    urls = state.get("urls_to_crawl", [])
    search_results = state.get("search_results", [])
    
    # Limit URLs based on mode config
    max_sources = mode_config.max_sources_to_crawl if mode_config else 15
    if len(urls) > max_sources:
        logger.info(f"Limiting crawl from {len(urls)} to {max_sources} URLs (mode limit)")
        urls = urls[:max_sources]
    
    logger.info(f"Crawling {len(urls)} URLs")
    
    if not urls:
        return {
            "phase": AgentPhase.PROCESSING,
            "crawl_results": [],
            "stream_events": [{
                "type": "crawl_complete",
                "data": {"crawled": 0, "failed": 0}
            }]
        }
    
    try:
        # Create URL to search result mapping for metadata
        url_metadata = {
            r.url: {"title": r.title, "snippet": r.snippet}
            for r in search_results
        }
        
        # Batch crawl
        batch_result = await services.crawl_service.crawl_many(urls)
        
        successful = [r for r in batch_result.results if r.is_success]
        failures = [
            {"url": r.url, "error": r.error_message or "Unknown error"}
            for r in batch_result.results if not r.is_success
        ]
        
        elapsed = time.time() - start_time
        
        return {
            "crawl_results": successful,
            "crawl_failures": failures,
            "phase": AgentPhase.PROCESSING,
            "timing": {**state.get("timing", {}), "crawl": elapsed},
            "stream_events": [{
                "type": "crawl_complete",
                "data": {
                    "crawled": len(successful),
                    "failed": len(failures)
                }
            }]
        }
        
    except CrawlError as e:
        logger.error(f"Crawl error: {e}")
        return {
            "phase": AgentPhase.PROCESSING,  # Continue with what we have
            "crawl_results": [],
            "errors": [{"phase": "crawl", "error": str(e)}]
        }


# =============================================================================
# PROCESS NODE
# =============================================================================

async def process_node(state: ResearchState) -> dict[str, Any]:
    """
    Process crawled content.
    
    Cleans, chunks, scores, and extracts facts from content.
    Builds citation map.
    
    Args:
        state: Current research state
        
    Returns:
        State updates with processed documents
    """
    start_time = time.time()
    services = get_services()
    mode_config = state.get("mode_config")
    
    crawl_results = state.get("crawl_results", [])
    search_results = state.get("search_results", [])
    query = state.get("query", "")
    
    min_quality = mode_config.min_quality_score if mode_config else 0.3
    logger.info(f"Processing {len(crawl_results)} documents (min quality: {min_quality})")
    
    if not crawl_results:
        # No content to process - go to reflection
        return {
            "phase": AgentPhase.REFLECTING,
            "processed_documents": [],
            "stream_events": [{
                "type": "processing_complete",
                "data": {"documents": 0}
            }]
        }
    
    # Get or create citation manager
    citation_manager = services.get_citation_manager()
    
    # Register sources from search results first
    for result in search_results:
        citation_manager.register_source_from_search(result)
    
    processed_docs = []
    extracted_facts = []
    
    # Create extractor once outside the loop (avoids re-compiling regex per crawl result)
    from src.processing.extractor import QuickFactExtractor
    quick_extractor = QuickFactExtractor()
    
    def _process_all_docs():
        """CPU-bound processing — runs in executor to avoid blocking the event loop."""
        _docs = []
        _facts = []
        for crawl_result in crawl_results:
            try:
                # Register crawl result as source
                citation_manager.register_source_from_crawl(crawl_result)
                
                # Clean content
                cleaned = services.cleaner.clean(crawl_result.content)
                
                # Score quality
                quality_score = services.scorer.score_source(
                    crawl_result=crawl_result,
                    query=query
                )
                
                # Only process high-quality content based on mode
                if quality_score < min_quality:
                    logger.debug(f"Skipping low-quality content: {crawl_result.url} (score: {quality_score:.2f} < {min_quality})")
                    continue
                
                # Chunk for processing
                chunks = services.chunker.chunk(
                    cleaned,
                    source_url=crawl_result.url,
                    source_title=crawl_result.title or ""
                )
                
                # Create processed document
                from src.processing.models import ProcessedDocument
                doc = ProcessedDocument(
                    url=crawl_result.url,
                    title=crawl_result.title or "",
                    original_content=cleaned,
                    chunks=chunks,
                    quality_score=quality_score,
                )
                _docs.append(doc)
                
                # Extract facts from each chunk
                for chunk in chunks:
                    chunk_facts = quick_extractor.extract_facts(chunk)
                    for fact in chunk_facts:
                        _facts.append({
                            "fact": fact.content,
                            "source_url": crawl_result.url,
                            "confidence": fact.confidence,
                            "type": fact.category or "general"
                        })
                    
            except Exception as e:
                logger.warning(f"Error processing {crawl_result.url}: {e}")
                continue
        
        # Sort by quality
        _docs.sort(key=lambda d: d.quality_score, reverse=True)
        return _docs, _facts
    
    # Run CPU-bound processing off the event loop
    loop = asyncio.get_event_loop()
    processed_docs, extracted_facts = await loop.run_in_executor(None, _process_all_docs)
    
    elapsed = time.time() - start_time
    
    return {
        "processed_documents": processed_docs,
        "extracted_facts": extracted_facts,
        "citation_map": citation_manager.citation_map,
        "phase": AgentPhase.REFLECTING,
        "timing": {**state.get("timing", {}), "processing": elapsed},
        "stream_events": [{
            "type": "processing_complete",
            "data": {
                "documents": len(processed_docs),
                "facts": len(extracted_facts)
            }
        }]
    }


# =============================================================================
# REFLECT NODE
# =============================================================================

async def reflect_node(state: ResearchState) -> dict[str, Any]:
    """
    Reflect on gathered information.
    
    Evaluates completeness and identifies gaps.
    Decides whether more research is needed.
    
    Args:
        state: Current research state
        
    Returns:
        State updates with reflection results
    """
    start_time = time.time()
    services = get_services()
    mode_config = state.get("mode_config")
    
    # Skip reflection if disabled in mode
    if mode_config and not mode_config.enable_reflection:
        logger.info("Reflection disabled for this mode - proceeding to synthesis")
        return {
            "needs_more_research": False,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "phase": AgentPhase.SYNTHESIZING,
            "stream_events": [{
                "type": "reflection_skipped",
                "data": {"reason": "Disabled in mode config"}
            }]
        }
    
    query = state.get("query", "")
    plan = state.get("research_plan", {})
    documents = state.get("processed_documents", [])
    facts = state.get("extracted_facts", [])
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    
    logger.info(f"Reflecting on research (iteration {iteration + 1}/{max_iterations})")
    
    # Quick path: if we have enough content, go to synthesis
    if len(documents) >= 5 and len(facts) >= 10:
        return {
            "needs_more_research": False,
            "iteration_count": iteration + 1,
            "phase": AgentPhase.SYNTHESIZING,
            "stream_events": [{
                "type": "reflection_complete",
                "data": {
                    "needs_more_research": False,
                    "reason": "Sufficient information gathered"
                }
            }]
        }
    
    # Use LLM for deeper reflection
    try:
        response = await services.llm_service.generate(
            prompt=REFLECTION_USER.format(
                query=query,
                intent=plan.get("intent", query),
                gathered_info=format_gathered_info(documents),
                source_count=len(documents),
                fact_count=len(facts),
                iteration=iteration + 1,
                max_iterations=max_iterations
            ),
            system=REFLECTION_SYSTEM
        )
        
        # Parse reflection
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            reflection = json.loads(content.strip())
        except json.JSONDecodeError:
            # Fallback
            reflection = {
                "completeness_score": 0.5,
                "knowledge_gaps": [],
                "needs_more_research": False,
                "suggested_queries": []
            }
        
        needs_more = (
            reflection.get("needs_more_research", False)
            and iteration < max_iterations - 1
            and reflection.get("completeness_score", 1.0) < 0.7
        )
        
        # If we need more research, add suggested queries
        new_sub_queries = []
        if needs_more:
            new_sub_queries = reflection.get("suggested_queries", [])[:3]
        
        elapsed = time.time() - start_time
        
        next_phase = AgentPhase.SEARCHING if needs_more else AgentPhase.SYNTHESIZING
        
        return {
            "knowledge_gaps": reflection.get("knowledge_gaps", []),
            "needs_more_research": needs_more,
            "iteration_count": iteration + 1,
            "sub_queries": new_sub_queries if needs_more else state.get("sub_queries", []),
            "phase": next_phase,
            "timing": {**state.get("timing", {}), f"reflection_{iteration + 1}": elapsed},
            "stream_events": [{
                "type": "reflection_complete",
                "data": {
                    "needs_more_research": needs_more,
                    "completeness": reflection.get("completeness_score", 0.5),
                    "gaps": reflection.get("knowledge_gaps", [])
                }
            }]
        }
        
    except LLMError as e:
        logger.warning(f"Reflection LLM error: {e}, proceeding to synthesis")
        return {
            "needs_more_research": False,
            "iteration_count": iteration + 1,
            "phase": AgentPhase.SYNTHESIZING,
            "errors": [{"phase": "reflection", "error": str(e)}]
        }


# =============================================================================
# SYNTHESIZE NODE
# =============================================================================

async def synthesize_node(state: ResearchState) -> dict[str, Any]:
    """
    Synthesize final answer.
    
    Creates comprehensive answer with citations from all sources.
    
    Args:
        state: Current research state
        
    Returns:
        State updates with final answer
    """
    start_time = time.time()
    services = get_services()
    mode_config = state.get("mode_config")
    
    query = state.get("query", "")
    documents = state.get("processed_documents", [])
    citation_map = state.get("citation_map")
    gaps = state.get("knowledge_gaps", [])
    
    # Get limits from mode config
    max_sources = mode_config.max_sources_for_synthesis if mode_config else 5
    max_chunks = mode_config.max_chunks_for_synthesis if mode_config else 50
    
    logger.info(f"Synthesizing answer from {len(documents)} sources (limits: {max_sources} sources, {max_chunks} chunks)")
    
    if not documents:
        return {
            "final_answer": "I couldn't find sufficient information to answer your query. Please try rephrasing or providing more context.",
            "answer_with_citations": "",
            "phase": AgentPhase.COMPLETE,
            "stream_events": [{
                "type": "synthesis_complete",
                "data": {"has_answer": False}
            }]
        }
    
    # Limit sources based on mode config
    if len(documents) > max_sources:
        documents = documents[:max_sources]
        logger.info(f"Limited to top {len(documents)} sources for synthesis")
    
    # Build citation manager from state if needed
    citation_manager = CitationManager()
    if citation_map:
        citation_manager.citation_map = citation_map
    else:
        # Register documents as sources
        for doc in documents:
            from src.services.crawl.models import CrawlResult, CrawlStatus
            mock_crawl = CrawlResult(
                url=doc.url,
                status=CrawlStatus.SUCCESS,
                content=doc.original_content,
                title=doc.title
            )
            citation_manager.register_source_from_crawl(mock_crawl, doc.quality_score)
    
    # Collect all chunks from documents for context building
    all_chunks = []
    for doc in documents:
        all_chunks.extend(doc.chunks)
    
    # Limit chunks based on mode config
    if len(all_chunks) > max_chunks:
        all_chunks = all_chunks[:max_chunks]
        logger.info(f"Limited to {max_chunks} chunks for synthesis")
    else:
        logger.info(f"Using {len(all_chunks)} chunks for synthesis")
    
    # Build context with citation markers (expects ContentChunk objects)
    context_with_markers = citation_manager.build_context_with_markers(all_chunks)
    
    # Format sources for prompt
    sources_formatted = []
    for doc in documents[:10]:  # Top 10 sources
        # Generate source ID from URL (same logic as CitationManager)
        import hashlib
        source_id = hashlib.sha256(doc.url.encode()).hexdigest()[:16]
        source = citation_manager.citation_map.sources.get(source_id)
        if source:
            sources_formatted.append({
                "index": source.citation_index,
                "title": doc.title,
                "url": doc.url,
                "content": doc.original_content[:1500]
            })
        else:
            # If not in citation_map, add directly
            sources_formatted.append({
                "index": len(sources_formatted) + 1,
                "title": doc.title,
                "url": doc.url,
                "content": doc.original_content[:1500]
            })
    
    # Choose prompt based on whether we have gaps
    if gaps:
        prompt = SYNTHESIS_WITH_GAPS.format(
            query=query,
            sources_with_citations=format_sources_for_synthesis(sources_formatted),
            gaps=format_gaps_list(gaps)
        )
    else:
        prompt = SYNTHESIS_USER.format(
            query=query,
            sources_with_citations=format_sources_for_synthesis(sources_formatted)
        )
    
    try:
        response = await services.llm_service.generate(
            prompt=prompt,
            system=SYNTHESIS_SYSTEM
        )
        
        answer = response.content
        
        # Annotate with proper citations
        answer_with_citations = citation_manager.annotate_answer(answer)
        
        elapsed = time.time() - start_time
        
        return {
            "draft_answer": answer,
            "final_answer": answer,
            "answer_with_citations": answer_with_citations,
            "phase": AgentPhase.COMPLETE,
            "timing": {**state.get("timing", {}), "synthesis": elapsed},
            "stream_events": [{
                "type": "synthesis_complete",
                "data": {
                    "has_answer": True,
                    "word_count": len(answer.split()),
                    "sources_used": len(sources_formatted)
                }
            }]
        }
        
    except LLMError as e:
        logger.error(f"Synthesis error: {e}")
        
        # Fallback: create basic answer from document content
        if documents:
            fallback = f"Based on my research about '{query}':\n\n"
            # Use first few chunks from top-quality documents
            fact_points = []
            for doc in documents[:3]:  # Top 3 sources
                for chunk in doc.chunks[:3]:  # First 3 chunks per source
                    # Extract first clean sentence from chunk
                    sentences = [s.strip() for s in chunk.content.split('.') if len(s.strip()) > 30]
                    if sentences:
                        fact_points.append(sentences[0] + ".")
                    if len(fact_points) >= 5:
                        break
                if len(fact_points) >= 5:
                    break
            
            fallback += "\n".join(f"- {fact}" for fact in fact_points)
            
            # Add sources
            fallback += "\n\nSources:\n"
            for i, doc in enumerate(documents[:3], 1):
                fallback += f"{i}. {doc.title or doc.url}\n"
            
            return {
                "final_answer": fallback,
                "phase": AgentPhase.COMPLETE,
                "errors": [{"phase": "synthesis", "error": str(e)}]
            }
        
        return {
            "final_answer": "I encountered an error while synthesizing the answer. Please try again.",
            "phase": AgentPhase.ERROR,
            "errors": [{"phase": "synthesis", "error": str(e)}]
        }


# =============================================================================
# ERROR HANDLER NODE
# =============================================================================

async def error_handler_node(state: ResearchState) -> dict[str, Any]:
    """
    Handle errors and attempt recovery.
    
    Args:
        state: Current research state
        
    Returns:
        State updates with error handling results
    """
    errors = state.get("errors", [])
    phase = state.get("phase", AgentPhase.ERROR)
    
    logger.error(f"Error handler invoked. Errors: {errors}")
    
    # Create user-friendly error message
    error_message = "I encountered some issues during research:\n"
    for error in errors[-3:]:  # Last 3 errors
        error_message += f"- {error.get('phase', 'unknown')}: {error.get('error', 'Unknown error')}\n"
    
    return {
        "final_answer": error_message + "\nPlease try again or rephrase your query.",
        "phase": AgentPhase.COMPLETE,
        "stream_events": [{
            "type": "error",
            "data": {"errors": errors}
        }]
    }
