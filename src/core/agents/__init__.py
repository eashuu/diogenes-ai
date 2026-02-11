"""
Multi-Agent System for Diogenes v2.0.

Provides specialized agents that collaborate to perform research:
- Coordinator: Orchestrates the research process
- Researcher: Gathers information from sources
- Verifier: Fact-checks and validates claims
- Writer: Synthesizes answers with citations
- Orchestrator: Main entry point for research workflow

Imports are lazy to avoid a fragile transitive import chain where a single
module-level error would collapse the entire package.
"""

# Protocol and Base are lightweight with no heavy transitive deps — safe to import eagerly
from src.core.agents.protocol import (
    MessageType,
    Priority,
    TaskType,
    AgentMessage,
    TaskAssignment,
    TaskResult,
)
from src.core.agents.base import (
    BaseAgent,
    AgentCapability,
    AgentStatus,
    AgentPool,
)


def __getattr__(name: str):
    """Lazy import for agent classes to avoid fragile transitive import chains."""
    # TODO: B3 — This lazy import pattern prevents a single agent file error
    # from collapsing the entire package. Consider removing once all agent
    # modules are stabilized and have proper test coverage.
    _lazy_imports = {
        "CoordinatorAgent": ("src.core.agents.coordinator", "CoordinatorAgent"),
        "ResearcherAgent": ("src.core.agents.researcher", "ResearcherAgent"),
        "VerifierAgent": ("src.core.agents.verifier", "VerifierAgent"),
        "WriterAgent": ("src.core.agents.writer", "WriterAgent"),
        "SuggestionAgent": ("src.core.agents.suggester", "SuggestionAgent"),
        "SuggestionResult": ("src.core.agents.suggester", "SuggestionResult"),
        "TransformerAgent": ("src.core.agents.transformer", "TransformerAgent"),
        "TransformResult": ("src.core.agents.transformer", "TransformResult"),
        "QuickAction": ("src.core.agents.transformer", "QuickAction"),
        "quick_transform": ("src.core.agents.transformer", "quick_transform"),
        "ResearchOrchestrator": ("src.core.agents.orchestrator", "ResearchOrchestrator"),
        "ResearchResult": ("src.core.agents.orchestrator", "ResearchResult"),
        "ResearchProgress": ("src.core.agents.orchestrator", "ResearchProgress"),
        "ResearchPhase": ("src.core.agents.orchestrator", "ResearchPhase"),
        "create_orchestrator": ("src.core.agents.orchestrator", "create_orchestrator"),
    }

    if name in _lazy_imports:
        module_path, attr_name = _lazy_imports[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Protocol
    "MessageType",
    "Priority",
    "TaskType",
    "AgentMessage",
    "TaskAssignment",
    "TaskResult",
    # Base
    "BaseAgent",
    "AgentCapability",
    "AgentStatus",
    "AgentPool",
    # Agents (lazy)
    "CoordinatorAgent",
    "ResearcherAgent",
    "VerifierAgent",
    "WriterAgent",
    "SuggestionAgent",
    "SuggestionResult",
    "TransformerAgent",
    "TransformResult",
    "QuickAction",
    "quick_transform",
    # Orchestrator (lazy)
    "ResearchOrchestrator",
    "ResearchResult",
    "ResearchProgress",
    "ResearchPhase",
    "create_orchestrator",
]
