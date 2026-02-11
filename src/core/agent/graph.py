"""
LangGraph Research Agent Graph Definition.

Defines the state machine graph that orchestrates the research process.
Uses LangGraph for structured agent execution with conditional routing.
"""

from typing import Any, Literal
from langgraph.graph import StateGraph, END

from src.utils.logging import get_logger
from src.core.agent.state import (
    ResearchState,
    AgentPhase,
    create_initial_state
)
from src.core.agent.modes import SearchMode
from src.core.agent.nodes import (
    plan_node,
    search_node,
    crawl_node,
    process_node,
    reflect_node,
    synthesize_node,
    error_handler_node
)


logger = get_logger(__name__)


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_after_reflection(
    state: ResearchState
) -> Literal["search", "synthesize"]:
    """
    Route after reflection node.
    
    Decides whether to do more research or synthesize.
    
    Args:
        state: Current research state
        
    Returns:
        Next node name
    """
    needs_more = state.get("needs_more_research", False)
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if needs_more and iteration < max_iterations:
        logger.info(f"Continuing research (iteration {iteration}/{max_iterations})")
        return "search"
    
    logger.info("Proceeding to synthesis")
    return "synthesize"


def route_on_phase(state: ResearchState) -> str:
    """
    Route based on current phase.
    
    Used for dynamic routing when phase changes.
    
    Args:
        state: Current research state
        
    Returns:
        Next node name or END
    """
    phase = state.get("phase", AgentPhase.PLANNING)
    
    phase_to_node = {
        AgentPhase.PLANNING: "plan",
        AgentPhase.SEARCHING: "search",
        AgentPhase.CRAWLING: "crawl",
        AgentPhase.PROCESSING: "process",
        AgentPhase.REFLECTING: "reflect",
        AgentPhase.SYNTHESIZING: "synthesize",
        AgentPhase.ERROR: "error_handler",
        AgentPhase.COMPLETE: END
    }
    
    return phase_to_node.get(phase, END)


def should_handle_error(state: ResearchState) -> bool:
    """Check if we should route to error handler."""
    return state.get("phase") == AgentPhase.ERROR


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def build_research_graph() -> StateGraph:
    """
    Build the research agent graph.
    
    Creates a LangGraph StateGraph with all nodes and edges.
    
    Flow:
        plan -> search -> crawl -> process -> reflect
                   ^                            |
                   |____ (if needs more) _______|
                                                |
                                                v
                                            synthesize -> END
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph with state schema
    graph = StateGraph(ResearchState)
    
    # Add nodes
    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("crawl", crawl_node)
    graph.add_node("process", process_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("error_handler", error_handler_node)
    
    # Set entry point
    graph.set_entry_point("plan")
    
    # Add edges for main flow
    graph.add_edge("plan", "search")
    graph.add_edge("search", "crawl")
    graph.add_edge("crawl", "process")
    graph.add_edge("process", "reflect")
    
    # Conditional edge after reflection
    graph.add_conditional_edges(
        "reflect",
        route_after_reflection,
        {
            "search": "search",
            "synthesize": "synthesize"
        }
    )
    
    # Synthesize goes to END
    graph.add_edge("synthesize", END)
    
    # Error handler goes to END
    graph.add_edge("error_handler", END)
    
    return graph


def compile_research_graph():
    """
    Compile the research graph for execution.
    
    Returns:
        Compiled graph that can be invoked
    """
    graph = build_research_graph()
    return graph.compile()


# =============================================================================
# RESEARCH AGENT CLASS
# =============================================================================

class ResearchAgent:
    """
    High-level research agent interface.
    
    Wraps the LangGraph execution with a clean API.
    Supports multiple research modes with different depth/speed tradeoffs.
    """
    
    def __init__(
        self,
        mode: SearchMode = SearchMode.BALANCED,
        max_iterations: int | None = None
    ):
        """
        Initialize the research agent.
        
        Args:
            mode: Research mode (quick, balanced, full, research, deep)
            max_iterations: Optional override for max research iterations
        """
        self.mode = mode
        self.max_iterations = max_iterations
        self._graph = None
    
    @property
    def graph(self):
        """Lazily compile the graph."""
        if self._graph is None:
            self._graph = compile_research_graph()
        return self._graph
    
    async def research(
        self,
        query: str,
        session_id: str | None = None,
        mode: SearchMode | None = None
    ) -> ResearchState:
        """
        Execute a research query.
        
        Args:
            query: The research question
            session_id: Optional session ID for tracking
            mode: Optional mode override for this query
            
        Returns:
            Final research state with answer
        """
        import uuid
        
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Use provided mode or fall back to instance mode
        research_mode = mode or self.mode
        
        logger.info(f"Starting research: {query[:100]}... (session: {session_id}, mode: {research_mode.value})")
        
        # Create initial state with mode
        initial_state = create_initial_state(
            query=query,
            session_id=session_id,
            mode=research_mode,
            max_iterations=self.max_iterations
        )
        
        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)
        
        logger.info(f"Research complete (session: {session_id})")
        
        return final_state
    
    async def research_stream(
        self,
        query: str,
        session_id: str | None = None,
        mode: SearchMode | None = None
    ):
        """
        Execute research with streaming updates.
        
        Yields state updates as the research progresses.
        
        Args:
            query: The research question
            session_id: Optional session ID for tracking
            mode: Optional mode override for this query
            
        Yields:
            State updates during research
        """
        import uuid
        
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        logger.info(f"Starting streaming research: {query[:100]}...")
        
        # Use provided mode or fall back to instance mode
        research_mode = mode or self.mode
        
        initial_state = create_initial_state(
            query=query,
            session_id=session_id,
            mode=research_mode,
            max_iterations=self.max_iterations
        )
        
        # Stream through graph execution
        async for state_update in self.graph.astream(initial_state):
            # Extract the node name and state
            for node_name, node_state in state_update.items():
                yield {
                    "node": node_name,
                    "phase": node_state.get("phase", AgentPhase.PLANNING),
                    "events": node_state.get("stream_events", []),
                    "state": node_state
                }
    
    def get_answer(self, state: ResearchState) -> str:
        """Extract the final answer from state."""
        return state.get("answer_with_citations") or state.get("final_answer", "")
    
    def get_sources(self, state: ResearchState) -> list[dict]:
        """Extract source cards from state."""
        citation_map = state.get("citation_map")
        if citation_map and hasattr(citation_map, 'sources'):
            return [
                {
                    "index": s.citation_index,
                    "title": s.title,
                    "url": s.url,
                    "domain": s.domain,
                    "favicon_url": s.favicon_url
                }
                for s in citation_map.sources.values()
            ]
        return []
    
    def get_timing(self, state: ResearchState) -> dict[str, float]:
        """Extract timing information from state."""
        return state.get("timing", {})


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def quick_research(query: str) -> tuple[str, list[dict]]:
    """
    Quick research helper function.
    
    Args:
        query: Research question
        
    Returns:
        Tuple of (answer, sources)
    """
    agent = ResearchAgent(max_iterations=2)
    state = await agent.research(query)
    
    return agent.get_answer(state), agent.get_sources(state)


def create_agent(max_iterations: int = 3) -> ResearchAgent:
    """
    Factory function to create a research agent.
    
    Args:
        max_iterations: Maximum research iterations
        
    Returns:
        Configured ResearchAgent instance
    """
    return ResearchAgent(max_iterations=max_iterations)
