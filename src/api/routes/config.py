"""
Configuration Management API routes.

GET/POST endpoints for reading and updating client-facing configuration.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import get_settings, apply_runtime_overrides
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/config", tags=["config"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ConfigResponse(BaseModel):
    """Full client-facing configuration."""

    # Search
    search_url: str
    search_timeout: float
    search_max_results: int
    search_language: str

    # LLM
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int

    # Processing
    max_chunk_size: int
    min_relevance_score: float
    max_sources: int

    # Agent
    max_iterations: int
    verification_threshold: float
    enable_knowledge_graph: bool
    enable_memory: bool

    # API
    api_host: str
    api_port: int
    cors_origins: list[str]


class ConfigUpdateRequest(BaseModel):
    """Partial config update. Only provided fields are applied."""

    # Search overrides
    search_url: str | None = None
    search_timeout: float | None = None
    search_max_results: int | None = None
    search_language: str | None = None

    # LLM overrides
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_temperature: float | None = None
    llm_max_tokens: int | None = None

    # Processing overrides
    max_chunk_size: int | None = None
    min_relevance_score: float | None = None
    max_sources: int | None = None

    # Agent overrides
    max_iterations: int | None = None
    verification_threshold: float | None = None
    enable_knowledge_graph: bool | None = None
    enable_memory: bool | None = None


# =============================================================================
# HELPERS
# =============================================================================


def _build_config_response() -> ConfigResponse:
    """Build a ConfigResponse from current settings."""
    s = get_settings()
    return ConfigResponse(
        search_url=s.search.base_url,
        search_timeout=s.search.timeout,
        search_max_results=s.search.max_results,
        search_language=s.search.language,
        llm_provider=s.llm.provider,
        llm_model=s.llm.models.planner,
        llm_temperature=s.llm.temperature,
        llm_max_tokens=s.llm.max_tokens,
        max_chunk_size=s.processing.max_chunk_size,
        min_relevance_score=s.processing.min_relevance_score,
        max_sources=s.processing.max_sources,
        max_iterations=s.agent.max_iterations,
        verification_threshold=s.agent.verification_threshold,
        enable_knowledge_graph=s.agent.enable_knowledge_graph,
        enable_memory=s.agent.enable_memory,
        api_host=s.api.host,
        api_port=s.api.port,
        cors_origins=s.api.cors_origins,
    )


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """Return the current client-facing configuration."""
    return _build_config_response()


@router.post("/", response_model=ConfigResponse)
async def update_config(req: ConfigUpdateRequest):
    """
    Partially update runtime configuration.

    Only fields that are explicitly set (non-None) in the request body are
    applied.  Changes are stored as runtime overrides — the on-disk YAML is
    **not** mutated.  Overrides persist until the process is restarted.
    """
    try:
        # Collect overrides per section
        search_updates: dict[str, Any] = {}
        llm_updates: dict[str, Any] = {}
        processing_updates: dict[str, Any] = {}
        agent_updates: dict[str, Any] = {}

        if req.search_url is not None:
            search_updates["base_url"] = req.search_url
        if req.search_timeout is not None:
            search_updates["timeout"] = req.search_timeout
        if req.search_max_results is not None:
            search_updates["max_results"] = req.search_max_results
        if req.search_language is not None:
            search_updates["language"] = req.search_language

        if req.llm_provider is not None:
            llm_updates["provider"] = req.llm_provider
        if req.llm_model is not None:
            llm_updates["models"] = {"planner": req.llm_model}
        if req.llm_temperature is not None:
            llm_updates["temperature"] = req.llm_temperature
        if req.llm_max_tokens is not None:
            llm_updates["max_tokens"] = req.llm_max_tokens

        if req.max_chunk_size is not None:
            processing_updates["max_chunk_size"] = req.max_chunk_size
        if req.min_relevance_score is not None:
            processing_updates["min_relevance_score"] = req.min_relevance_score
        if req.max_sources is not None:
            processing_updates["max_sources"] = req.max_sources

        if req.max_iterations is not None:
            agent_updates["max_iterations"] = req.max_iterations
        if req.verification_threshold is not None:
            agent_updates["verification_threshold"] = req.verification_threshold
        if req.enable_knowledge_graph is not None:
            agent_updates["enable_knowledge_graph"] = req.enable_knowledge_graph
        if req.enable_memory is not None:
            agent_updates["enable_memory"] = req.enable_memory

        # Apply
        if search_updates:
            apply_runtime_overrides("search", search_updates)
        if llm_updates:
            apply_runtime_overrides("llm", llm_updates)
        if processing_updates:
            apply_runtime_overrides("processing", processing_updates)
        if agent_updates:
            apply_runtime_overrides("agent", agent_updates)

        logger.info("Config updated via API", extra={
            "search": search_updates, "llm": llm_updates,
            "processing": processing_updates, "agent": agent_updates,
        })

        return _build_config_response()

    except Exception as exc:
        logger.error("Config update failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
