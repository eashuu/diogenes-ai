"""
Research Agent State Management.

Defines the state schema for the LangGraph research agent.
Uses TypedDict for compatibility with LangGraph's state management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict

from src.services.search.models import SearchResult
from src.services.crawl.models import CrawlResult
from src.processing.models import ProcessedDocument
from src.core.citation.models import CitationMap
from src.core.agent.modes import SearchMode, ModeConfig


class AgentPhase(str, Enum):
    """Current phase of the research agent."""
    PLANNING = "planning"
    SEARCHING = "searching"
    CRAWLING = "crawling"
    PROCESSING = "processing"
    REFLECTING = "reflecting"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    ERROR = "error"


class ResearchState(TypedDict, total=False):
    """
    State schema for the research agent.
    
    This TypedDict defines all state that flows through the LangGraph.
    Using total=False makes all fields optional for incremental updates.
    """
    # Input
    query: str
    session_id: str
    mode: SearchMode
    mode_config: ModeConfig
    
    # Planning
    research_plan: dict[str, Any]
    sub_queries: list[str]
    search_strategies: list[str]
    
    # Search results
    search_results: list[SearchResult]
    search_results_by_query: dict[str, list[SearchResult]]
    
    # Crawl results
    urls_to_crawl: list[str]
    crawl_results: list[CrawlResult]
    crawl_failures: list[dict[str, str]]
    
    # Processing
    processed_documents: list[ProcessedDocument]
    extracted_facts: list[dict[str, Any]]
    
    # Citations
    citation_map: CitationMap
    
    # Reflection
    knowledge_gaps: list[str]
    needs_more_research: bool
    iteration_count: int
    max_iterations: int
    
    # Synthesis
    draft_answer: str
    final_answer: str
    answer_with_citations: str
    
    # Metadata
    phase: AgentPhase
    errors: list[dict[str, Any]]
    timing: dict[str, float]
    
    # Streaming
    stream_events: list[dict[str, Any]]


@dataclass
class ResearchContext:
    """
    Rich context object for passing between nodes.
    
    Provides helper methods for common operations.
    """
    state: ResearchState
    
    @property
    def query(self) -> str:
        """Get the original query."""
        return self.state.get("query", "")
    
    @property
    def iteration(self) -> int:
        """Get current iteration count."""
        return self.state.get("iteration_count", 0)
    
    @property
    def max_iterations(self) -> int:
        """Get maximum allowed iterations."""
        return self.state.get("max_iterations", 3)
    
    @property
    def can_iterate(self) -> bool:
        """Check if more iterations are allowed."""
        return self.iteration < self.max_iterations
    
    @property
    def has_sufficient_sources(self) -> bool:
        """Check if we have enough sources to synthesize."""
        docs = self.state.get("processed_documents", [])
        return len(docs) >= 2
    
    @property
    def total_facts(self) -> int:
        """Get total extracted facts count."""
        return len(self.state.get("extracted_facts", []))
    
    def get_all_content(self) -> str:
        """Get all processed content concatenated."""
        docs = self.state.get("processed_documents", [])
        return "\n\n---\n\n".join(
            doc.cleaned_content for doc in docs
            if hasattr(doc, 'cleaned_content')
        )
    
    def get_top_sources(self, n: int = 5) -> list[ProcessedDocument]:
        """Get top N sources by quality score."""
        docs = self.state.get("processed_documents", [])
        sorted_docs = sorted(
            docs,
            key=lambda d: getattr(d, 'quality_score', 0),
            reverse=True
        )
        return sorted_docs[:n]


def create_initial_state(
    query: str,
    session_id: str,
    mode: SearchMode = SearchMode.BALANCED,
    max_iterations: int | None = None
) -> ResearchState:
    """
    Create initial state for a new research session.
    
    Args:
        query: The user's research query
        session_id: Unique session identifier
        mode: Research mode (quick, balanced, full, research, deep)
        max_iterations: Maximum reflection iterations (overrides mode config)
        
    Returns:
        Initialized ResearchState
    """
    from src.core.agent.modes import get_mode_config
    
    mode_config = get_mode_config(mode)
    
    # Allow override of max_iterations
    if max_iterations is None:
        max_iterations = mode_config.max_iterations
    
    return ResearchState(
        query=query,
        session_id=session_id,
        mode=mode,
        mode_config=mode_config,
        research_plan={},
        sub_queries=[],
        search_strategies=[],
        search_results=[],
        search_results_by_query={},
        urls_to_crawl=[],
        crawl_results=[],
        crawl_failures=[],
        processed_documents=[],
        extracted_facts=[],
        citation_map=CitationMap(),
        knowledge_gaps=[],
        needs_more_research=False,
        iteration_count=0,
        max_iterations=max_iterations,
        draft_answer="",
        final_answer="",
        answer_with_citations="",
        phase=AgentPhase.PLANNING,
        errors=[],
        timing={},
        stream_events=[]
    )


def merge_state(
    current: ResearchState,
    updates: dict[str, Any]
) -> ResearchState:
    """
    Merge updates into current state.
    
    Handles list appending for accumulating fields.
    
    Args:
        current: Current state
        updates: Updates to apply
        
    Returns:
        New merged state
    """
    # Fields that should be appended rather than replaced
    append_fields = {
        "search_results",
        "crawl_results",
        "crawl_failures",
        "processed_documents",
        "extracted_facts",
        "knowledge_gaps",
        "errors",
        "stream_events"
    }
    
    merged = dict(current)
    
    for key, value in updates.items():
        if key in append_fields and key in merged:
            # Append to existing list
            existing = merged.get(key, [])
            if isinstance(existing, list) and isinstance(value, list):
                merged[key] = existing + value
            else:
                merged[key] = value
        else:
            # Replace value
            merged[key] = value
    
    return ResearchState(**merged)
