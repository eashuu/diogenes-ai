"""
Research Agent Package.

Provides the LangGraph-based research agent for autonomous research.
"""

from src.core.agent.state import (
    ResearchState,
    AgentPhase,
    ResearchContext,
    create_initial_state,
    merge_state
)
from src.core.agent.graph import (
    ResearchAgent,
    build_research_graph,
    compile_research_graph,
    quick_research,
    create_agent
)
from src.core.agent.nodes import (
    plan_node,
    search_node,
    crawl_node,
    process_node,
    reflect_node,
    synthesize_node,
    error_handler_node
)

__all__ = [
    # State
    "ResearchState",
    "AgentPhase",
    "ResearchContext",
    "create_initial_state",
    "merge_state",
    # Graph
    "ResearchAgent",
    "build_research_graph",
    "compile_research_graph",
    "quick_research",
    "create_agent",
    # Nodes
    "plan_node",
    "search_node",
    "crawl_node",
    "process_node",
    "reflect_node",
    "synthesize_node",
    "error_handler_node"
]
