"""
Research Orchestrator.

Main entry point for the multi-agent research system.
Manages the complete research workflow from query to final response.
"""

import asyncio
from typing import Any, AsyncIterator, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.utils.logging import get_logger
from src.core.agents import (
    AgentPool,
    CoordinatorAgent,
    ResearcherAgent,
    VerifierAgent,
    WriterAgent,
    SuggestionAgent,
    TaskAssignment,
    TaskType,
)
from src.core.agent.modes import SearchMode, ModeConfig, get_mode_config
from src.config import get_settings
from src.storage.memory_store import MemoryStore

logger = get_logger(__name__)


class ResearchPhase(str, Enum):
    """Phases of the research process."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    RESEARCHING = "researching"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    SYNTHESIZING = "synthesizing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ResearchProgress:
    """Tracks progress of a research session."""
    session_id: str
    query: str
    phase: ResearchPhase = ResearchPhase.INITIALIZING
    sub_phase: str = ""
    progress_pct: float = 0.0
    sources_found: int = 0
    sources_crawled: int = 0
    claims_verified: int = 0
    iterations: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    messages: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "query": self.query,
            "phase": self.phase.value,
            "sub_phase": self.sub_phase,
            "progress_pct": self.progress_pct,
            "sources_found": self.sources_found,
            "sources_crawled": self.sources_crawled,
            "claims_verified": self.claims_verified,
            "iterations": self.iterations,
            "elapsed_seconds": (datetime.now() - self.started_at).total_seconds(),
            "messages": self.messages[-5:],  # Last 5 messages
        }


@dataclass 
class ResearchResult:
    """Final result of a research session."""
    session_id: str
    query: str
    answer: str
    sources: list[dict]
    verified_claims: list[dict]
    contradictions: list[dict]
    reliability_score: float
    confidence: float
    mode: str
    iterations: int
    duration_seconds: float
    suggested_questions: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "query": self.query,
            "answer": self.answer,
            "sources": self.sources,
            "verified_claims": self.verified_claims,
            "contradictions": self.contradictions,
            "reliability_score": self.reliability_score,
            "confidence": self.confidence,
            "mode": self.mode,
            "iterations": self.iterations,
            "duration_seconds": self.duration_seconds,
            "suggested_questions": self.suggested_questions,
            "related_topics": self.related_topics,
            "metadata": self.metadata,
        }


class ResearchOrchestrator:
    """
    Orchestrates the complete multi-agent research workflow.
    
    This is the main interface for conducting research. It:
    1. Initializes and manages specialized agents
    2. Coordinates the research flow
    3. Streams progress updates
    4. Returns verified, cited research results
    """
    
    def __init__(
        self,
        mode: SearchMode = SearchMode.BALANCED,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            mode: Research mode determining depth/speed tradeoff
        """
        self._mode = mode
        self._mode_config = get_mode_config(mode)
        self._settings = None
        
        # Agent pool
        self._agent_pool: Optional[AgentPool] = None
        self._coordinator: Optional[CoordinatorAgent] = None
        self._researcher: Optional[ResearcherAgent] = None
        self._verifier: Optional[VerifierAgent] = None
        self._writer: Optional[WriterAgent] = None
        self._suggester: Optional[SuggestionAgent] = None
        
        # Memory store for user context
        self._memory_store: Optional[MemoryStore] = None
        
        # Session tracking
        self._session_counter = 0
    
    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings
    
    async def initialize(self) -> None:
        """Initialize all agents."""
        logger.info(f"Initializing ResearchOrchestrator in {self._mode.value} mode")
        
        # Create agent pool
        self._agent_pool = AgentPool()
        
        # Initialize specialized agents
        self._coordinator = CoordinatorAgent()
        self._researcher = ResearcherAgent()
        self._verifier = VerifierAgent()
        self._writer = WriterAgent()
        self._suggester = SuggestionAgent()
        
        # Register agents with the pool
        self._agent_pool.register(self._coordinator)
        self._agent_pool.register(self._researcher)
        self._agent_pool.register(self._verifier)
        self._agent_pool.register(self._writer)
        self._agent_pool.register(self._suggester)
        
        # Initialize memory store
        self._memory_store = MemoryStore()
        
        logger.info("All agents initialized and registered")
    
    async def research(
        self,
        query: str,
        context: Optional[str] = None,
        style: str = "comprehensive",
        user_id: str = "default",
    ) -> ResearchResult:
        """
        Conduct research on a query.
        
        Args:
            query: The research query
            context: Optional additional context
            style: Output style (comprehensive, brief, academic, technical)
            user_id: User ID for personalized memory context
            
        Returns:
            Complete research result
        """
        # Ensure initialized
        if self._coordinator is None:
            await self.initialize()
        
        # Generate session ID
        self._session_counter += 1
        session_id = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._session_counter}"
        
        start_time = datetime.now()
        progress = ResearchProgress(session_id=session_id, query=query)
        
        try:
            # Fetch user memory context (if enabled in config)
            memory_context = ""
            if self._memory_store:
                from src.config import get_settings as _get_settings
                if _get_settings().agent.enable_memory_context:
                    memory_context = await self._memory_store.build_context_string(
                        user_id=user_id,
                        query=query,
                        max_memories=10
                    )
                    if memory_context:
                        logger.debug(f"Injecting {len(memory_context)} chars of memory context for user {user_id}")
            
            # Combine provided context with memory context
            full_context = ""
            if memory_context:
                full_context = memory_context
            if context:
                full_context = f"{full_context}\n\n{context}" if full_context else context
            
            # Phase 1: Research via coordinator
            progress.phase = ResearchPhase.RESEARCHING
            progress.messages.append("Starting multi-agent research...")
            
            # Give coordinator access to the agent pool
            self._coordinator.agent_pool = self._agent_pool
            
            research_state = await self._coordinator.research(
                query=query,
                session_id=session_id,
                mode=self._mode,
                context=full_context if full_context else None,
            )
            
            # Extract data from state dict
            sources = research_state.get("sources", [])
            crawl_results = research_state.get("crawl_results", [])
            processed_docs = research_state.get("processed_documents", [])
            iterations = research_state.get("iteration_count", 1)
            
            progress.sources_found = len(sources) + len(crawl_results)
            progress.sources_crawled = len(crawl_results)
            progress.iterations = iterations
            
            # Build findings from crawl results and processed documents
            findings = []
            for doc in crawl_results:
                if isinstance(doc, dict):
                    findings.append({
                        "content": doc.get("content", doc.get("text", "")),
                        "url": doc.get("url", ""),
                        "title": doc.get("title", "")
                    })
            for doc in processed_docs:
                if isinstance(doc, dict):
                    findings.append(doc)
            
            # Build source list
            all_sources = []
            for src in sources:
                if isinstance(src, dict):
                    all_sources.append(src)
            for src in crawl_results:
                if isinstance(src, dict) and src.get("url"):
                    all_sources.append({
                        "url": src.get("url", ""),
                        "title": src.get("title", ""),
                        "content": src.get("content", "")[:500],
                        "crawled": True
                    })
            
            # Phase 2: Verification (only if enabled for this mode)
            verified_claims = []
            contradictions = []
            reliability_score = 0.8  # Default for non-verified modes
            
            if self._mode_config.enable_verification:
                progress.phase = ResearchPhase.VERIFYING
                progress.messages.append("Verifying claims...")
                
                # Use final_answer if available, otherwise use findings
                answer_to_verify = research_state.get("final_answer", "")
                if not answer_to_verify and findings:
                    answer_to_verify = "\n".join([
                        f.get("content", str(f))[:500]
                        for f in findings[:10]
                    ])
                
                verification_result = await self._verifier.verify_answer(
                    answer=answer_to_verify,
                    sources=all_sources
                )
                
                verified_claims = verification_result.get("verified_claims", [])
                contradictions = verification_result.get("contradictions", [])
                reliability_score = verification_result.get("reliability_score", 0.8)
                
                progress.claims_verified = len(verified_claims)
            else:
                logger.debug(f"Skipping verification for {self._mode.value} mode")
            
            # Phase 3: Synthesis
            progress.phase = ResearchPhase.SYNTHESIZING
            progress.messages.append("Synthesizing final answer...")
            
            # Check if coordinator already produced an answer
            existing_answer = research_state.get("final_answer", "") or research_state.get("answer_with_citations", "")
            
            if existing_answer:
                # Use existing answer from coordinator
                answer = existing_answer
                confidence = 0.8
            else:
                # Generate new answer via writer
                synthesis_result = await self._writer.synthesize_research(
                    query=query,
                    findings=findings,
                    sources=all_sources,
                    verified_claims=verified_claims,
                    style=style
                )
                
                answer = synthesis_result.get("content", "")
                confidence = synthesis_result.get("metrics", {}).get("quality_score", 0.8)
            
            # Generate follow-up suggestions
            suggested_questions = []
            related_topics = []
            if self._suggester:
                try:
                    # Use quick mode for non-deep research
                    quick_mode = self._mode in [SearchMode.QUICK, SearchMode.BALANCED]
                    source_titles = [s.get("title", "") for s in all_sources[:5]]
                    
                    suggestion_result = await self._suggester.generate_suggestions(
                        query=query,
                        answer=answer,
                        sources=source_titles,
                        entities=[],  # Could extract from research_state if available
                        quick=quick_mode
                    )
                    suggested_questions = suggestion_result.suggested_questions
                    related_topics = suggestion_result.related_topics
                    logger.debug(f"Generated {len(suggested_questions)} suggestions")
                except Exception as e:
                    logger.warning(f"Failed to generate suggestions: {e}")
            
            # Complete
            progress.phase = ResearchPhase.COMPLETE
            duration = (datetime.now() - start_time).total_seconds()
            
            return ResearchResult(
                session_id=session_id,
                query=query,
                answer=answer,
                sources=all_sources,
                verified_claims=verified_claims,
                contradictions=contradictions,
                reliability_score=reliability_score,
                confidence=confidence,
                mode=self._mode.value,
                iterations=progress.iterations,
                duration_seconds=duration,
                suggested_questions=suggested_questions,
                related_topics=related_topics,
                metadata={
                    "style": style,
                    "mode_config": {
                        "max_search_results": self._mode_config.max_search_results,
                        "max_sources_to_crawl": self._mode_config.max_sources_to_crawl,
                        "max_iterations": self._mode_config.max_iterations,
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            progress.phase = ResearchPhase.FAILED
            duration = (datetime.now() - start_time).total_seconds()
            
            return ResearchResult(
                session_id=session_id,
                query=query,
                answer=f"Research failed: {str(e)}",
                sources=[],
                verified_claims=[],
                contradictions=[],
                reliability_score=0.0,
                confidence=0.0,
                mode=self._mode.value,
                iterations=progress.iterations,
                duration_seconds=duration,
                metadata={"error": str(e)}
            )
    
    async def research_stream(
        self,
        query: str,
        context: Optional[str] = None,
        style: str = "comprehensive",
        user_id: str = "default",
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Conduct research with streaming progress updates.
        
        Args:
            query: The research query
            context: Optional additional context
            style: Output style
            user_id: User ID for personalized memory context
            
        Yields:
            Progress updates and final result
        """
        # Ensure initialized
        if self._coordinator is None:
            await self.initialize()
        
        # Generate session ID
        self._session_counter += 1
        session_id = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._session_counter}"
        
        start_time = datetime.now()
        progress = ResearchProgress(session_id=session_id, query=query)
        
        try:
            # Emit initial progress
            yield {"type": "progress", "data": progress.to_dict()}
            
            # Fetch user memory context (if enabled in config)
            memory_context = ""
            if self._memory_store:
                from src.config import get_settings as _get_settings
                if _get_settings().agent.enable_memory_context:
                    memory_context = await self._memory_store.build_context_string(
                        user_id=user_id,
                        query=query,
                        max_memories=10
                    )
                    if memory_context:
                        logger.debug(f"Injecting {len(memory_context)} chars of memory context for user {user_id}")
            
            # Combine provided context with memory context
            full_context = ""
            if memory_context:
                full_context = memory_context
            if context:
                full_context = f"{full_context}\n\n{context}" if full_context else context
            
            # Phase 1: Planning
            progress.phase = ResearchPhase.PLANNING
            progress.progress_pct = 0.1
            progress.messages.append("Creating research plan...")
            yield {"type": "progress", "data": progress.to_dict()}
            
            # Phase 2: Research
            progress.phase = ResearchPhase.RESEARCHING
            progress.progress_pct = 0.2
            progress.messages.append("Searching for information...")
            yield {"type": "progress", "data": progress.to_dict()}
            
            # Give coordinator access to the agent pool
            self._coordinator.agent_pool = self._agent_pool
            
            research_state = await self._coordinator.research(
                query=query,
                session_id=session_id,
                mode=self._mode,
                context=full_context if full_context else None,
            )
            
            # Extract data from state dict
            sources = research_state.get("sources", [])
            crawl_results = research_state.get("crawl_results", [])
            processed_docs = research_state.get("processed_documents", [])
            iterations = research_state.get("iteration_count", 1)
            
            progress.sources_found = len(sources) + len(crawl_results)
            progress.sources_crawled = len(crawl_results)
            progress.iterations = iterations
            progress.progress_pct = 0.5
            progress.messages.append(f"Found {progress.sources_found} sources")
            yield {"type": "progress", "data": progress.to_dict()}
            
            # Build findings and sources
            findings = []
            for doc in crawl_results:
                if isinstance(doc, dict):
                    findings.append({
                        "content": doc.get("content", doc.get("text", "")),
                        "url": doc.get("url", ""),
                        "title": doc.get("title", "")
                    })
            
            all_sources = []
            for src in sources:
                if isinstance(src, dict):
                    all_sources.append(src)
            for src in crawl_results:
                if isinstance(src, dict) and src.get("url"):
                    all_sources.append({
                        "url": src.get("url", ""),
                        "title": src.get("title", ""),
                        "content": src.get("content", "")[:500],
                        "crawled": True
                    })
            
            # Emit sources as they're found
            for source in all_sources[:5]:
                yield {
                    "type": "source",
                    "data": {
                        "url": source.get("url", ""),
                        "title": source.get("title", ""),
                    }
                }
            
            # Phase 3: Verification (only if enabled for this mode)
            verified_claims = []
            contradictions = []
            reliability_score = 0.8  # Default for non-verified modes
            
            if self._mode_config.enable_verification:
                progress.phase = ResearchPhase.VERIFYING
                progress.progress_pct = 0.6
                progress.messages.append("Verifying claims...")
                yield {"type": "progress", "data": progress.to_dict()}
                
                answer_to_verify = research_state.get("final_answer", "")
                if not answer_to_verify and findings:
                    answer_to_verify = "\n".join([
                        f.get("content", str(f))[:500]
                        for f in findings[:10]
                    ])
                
                verification_result = await self._verifier.verify_answer(
                    answer=answer_to_verify,
                    sources=all_sources
                )
                
                verified_claims = verification_result.get("verified_claims", [])
                contradictions = verification_result.get("contradictions", [])
                reliability_score = verification_result.get("reliability_score", 0.8)
                
                progress.claims_verified = len(verified_claims)
                progress.progress_pct = 0.75
                yield {"type": "progress", "data": progress.to_dict()}
            else:
                logger.debug(f"Skipping verification for {self._mode.value} mode (streaming)")
                progress.progress_pct = 0.75
            
            # Phase 4: Synthesis
            progress.phase = ResearchPhase.SYNTHESIZING
            progress.progress_pct = 0.85
            progress.messages.append("Synthesizing answer...")
            yield {"type": "progress", "data": progress.to_dict()}
            
            # Check if coordinator already produced an answer
            existing_answer = research_state.get("final_answer", "") or research_state.get("answer_with_citations", "")
            
            if existing_answer:
                answer = existing_answer
                confidence = 0.8
            else:
                synthesis_result = await self._writer.synthesize_research(
                    query=query,
                    findings=findings,
                    sources=all_sources,
                    verified_claims=verified_claims,
                    style=style
                )
                answer = synthesis_result.get("content", "")
                confidence = synthesis_result.get("metrics", {}).get("quality_score", 0.8)
            
            # Stream answer in chunks
            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i+chunk_size]
                yield {
                    "type": "answer_chunk",
                    "data": {"content": chunk}
                }
                # Yield control without artificial delay — SSE handles backpressure
                await asyncio.sleep(0)
            
            # Generate follow-up suggestions
            suggested_questions = []
            related_topics = []
            if self._suggester:
                try:
                    quick_mode = self._mode in [SearchMode.QUICK, SearchMode.BALANCED]
                    source_titles = [s.get("title", "") for s in all_sources[:5]]
                    
                    suggestion_result = await self._suggester.generate_suggestions(
                        query=query,
                        answer=answer,
                        sources=source_titles,
                        entities=[],
                        quick=quick_mode
                    )
                    suggested_questions = suggestion_result.suggested_questions
                    related_topics = suggestion_result.related_topics
                    
                    # Stream suggestions event
                    yield {
                        "type": "suggestions",
                        "data": {
                            "suggested_questions": suggested_questions,
                            "related_topics": related_topics
                        }
                    }
                except Exception as e:
                    logger.warning(f"Failed to generate suggestions: {e}")
            
            # Complete
            progress.phase = ResearchPhase.COMPLETE
            progress.progress_pct = 1.0
            duration = (datetime.now() - start_time).total_seconds()
            
            result = ResearchResult(
                session_id=session_id,
                query=query,
                answer=answer,
                sources=all_sources,
                verified_claims=verified_claims,
                contradictions=contradictions,
                reliability_score=reliability_score,
                confidence=confidence,
                mode=self._mode.value,
                iterations=progress.iterations,
                duration_seconds=duration,
                suggested_questions=suggested_questions,
                related_topics=related_topics,
                metadata={"style": style}
            )
            
            yield {"type": "complete", "data": result.to_dict()}
            
        except Exception as e:
            logger.error(f"Research stream failed: {e}")
            progress.phase = ResearchPhase.FAILED
            progress.messages.append(f"Error: {str(e)}")
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "progress": progress.to_dict()
                }
            }
    
    def get_agent_metrics(self) -> dict[str, Any]:
        """Get metrics from all agents."""
        if self._agent_pool is None:
            return {}
        
        return {
            "coordinator": self._coordinator.metrics.to_dict() if self._coordinator else {},
            "researcher": self._researcher.metrics.to_dict() if self._researcher else {},
            "verifier": self._verifier.metrics.to_dict() if self._verifier else {},
            "writer": self._writer.metrics.to_dict() if self._writer else {},
        }


# Convenience factory function
async def create_orchestrator(
    mode: SearchMode = SearchMode.BALANCED
) -> ResearchOrchestrator:
    """
    Create and initialize a research orchestrator.
    
    Args:
        mode: Research mode
        
    Returns:
        Initialized orchestrator
    """
    orchestrator = ResearchOrchestrator(mode=mode)
    await orchestrator.initialize()
    return orchestrator
