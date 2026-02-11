"""
Settings API Routes.

Provides endpoints for user settings, system configuration, and service status.
"""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

from src.config import get_settings, apply_runtime_overrides, clear_settings_cache
from src.utils.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

# Reuse a single httpx client for all service checks (connection pooling)
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Get or lazily create the shared httpx client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


# =============================================================================
# SCHEMAS
# =============================================================================

class LLMModelInfo(BaseModel):
    """Information about an available LLM model."""
    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization: Optional[str] = None
    family: Optional[str] = None


class LLMModelsConfig(BaseModel):
    """LLM model configuration for different tasks."""
    planner: str = Field(description="Model for query planning")
    extractor: str = Field(description="Model for fact extraction")
    synthesizer: str = Field(description="Model for answer synthesis")
    reflector: str = Field(description="Model for reflection/verification")


class LLMSettings(BaseModel):
    """LLM service settings."""
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    temperature: float = Field(ge=0.0, le=2.0, default=0.0)
    max_tokens: int = Field(ge=256, le=32768, default=4096)
    timeout: float = Field(ge=10.0, le=600.0, default=120.0)
    models: LLMModelsConfig


class SearchSettings(BaseModel):
    """Search service settings."""
    provider: str = "searxng"
    base_url: str = "http://localhost:8080"
    timeout: float = Field(ge=5.0, le=120.0, default=20.0)
    max_results: int = Field(ge=5, le=50, default=10)
    categories: list[str] = ["general", "science", "it"]
    language: str = "en-US"


class CrawlSettings(BaseModel):
    """Crawl service settings."""
    max_concurrent: int = Field(ge=1, le=20, default=5)
    timeout: float = Field(ge=10.0, le=120.0, default=30.0)
    max_content_length: int = Field(ge=50000, le=2000000, default=500000)


class AgentSettings(BaseModel):
    """Agent behavior settings."""
    max_iterations: int = Field(ge=1, le=10, default=3)
    min_sources: int = Field(ge=1, le=20, default=3)
    max_sources: int = Field(ge=3, le=30, default=8)
    coverage_threshold: float = Field(ge=0.0, le=1.0, default=0.7)


class UserPreferences(BaseModel):
    """User preferences for UI and behavior."""
    username: str = "Guest Researcher"
    user_title: str = "Pro Plan"
    language: str = "English"
    default_research_mode: str = "balanced"
    default_profile: str = "general"
    enable_suggestions: bool = True
    enable_verification: bool = True
    theme: str = "diogenes"


class SystemSettingsResponse(BaseModel):
    """Complete system settings response."""
    llm: LLMSettings
    search: SearchSettings
    crawl: CrawlSettings
    agent: AgentSettings
    user: UserPreferences
    version: str
    environment: str


class UpdateLLMSettingsRequest(BaseModel):
    """Request to update LLM settings."""
    provider: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=256, le=32768)
    timeout: Optional[float] = Field(None, ge=10.0, le=600.0)
    models: Optional[LLMModelsConfig] = None


class UpdateSearchSettingsRequest(BaseModel):
    """Request to update search settings."""
    base_url: Optional[str] = None
    timeout: Optional[float] = Field(None, ge=5.0, le=120.0)
    max_results: Optional[int] = Field(None, ge=5, le=50)
    categories: Optional[list[str]] = None
    language: Optional[str] = None


class UpdateAgentSettingsRequest(BaseModel):
    """Request to update agent settings."""
    max_iterations: Optional[int] = Field(None, ge=1, le=10)
    min_sources: Optional[int] = Field(None, ge=1, le=20)
    max_sources: Optional[int] = Field(None, ge=3, le=30)
    coverage_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class UpdateUserPreferencesRequest(BaseModel):
    """Request to update user preferences."""
    username: Optional[str] = None
    user_title: Optional[str] = None
    language: Optional[str] = None
    default_research_mode: Optional[str] = None
    default_profile: Optional[str] = None
    enable_suggestions: Optional[bool] = None
    enable_verification: Optional[bool] = None
    theme: Optional[str] = None


class ServiceStatusResponse(BaseModel):
    """Status of a service."""
    name: str
    status: str  # "online", "offline", "degraded"
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class AllServicesStatusResponse(BaseModel):
    """Status of all services."""
    ollama: ServiceStatusResponse
    searxng: ServiceStatusResponse
    overall: str  # "healthy", "degraded", "unhealthy"


# =============================================================================
# IN-MEMORY SETTINGS OVERRIDE (for runtime changes)
# =============================================================================

# These override the config file settings at runtime
_settings_overrides: dict = {
    "llm": {},
    "search": {},
    "crawl": {},
    "agent": {},
    "user": {
        "username": "Guest Researcher",
        "user_title": "Pro Plan",
        "language": "English",
        "default_research_mode": "balanced",
        "default_profile": "general",
        "enable_suggestions": True,
        "enable_verification": True,
        "theme": "diogenes"
    }
}


def _get_merged_settings() -> dict:
    """Merge config file settings with runtime overrides."""
    settings = get_settings()
    
    return {
        "llm": {
            "provider": _settings_overrides["llm"].get("provider", settings.llm.provider),
            "base_url": _settings_overrides["llm"].get("base_url", settings.llm.base_url),
            "temperature": _settings_overrides["llm"].get("temperature", settings.llm.temperature),
            "max_tokens": _settings_overrides["llm"].get("max_tokens", settings.llm.max_tokens),
            "timeout": _settings_overrides["llm"].get("timeout", settings.llm.timeout),
            "models": {
                "planner": _settings_overrides["llm"].get("models", {}).get("planner", settings.llm.models.planner),
                "extractor": _settings_overrides["llm"].get("models", {}).get("extractor", settings.llm.models.extractor),
                "synthesizer": _settings_overrides["llm"].get("models", {}).get("synthesizer", settings.llm.models.synthesizer),
                "reflector": _settings_overrides["llm"].get("models", {}).get("reflector", settings.llm.models.reflector),
            }
        },
        "search": {
            "provider": _settings_overrides["search"].get("provider", settings.search.provider),
            "base_url": _settings_overrides["search"].get("base_url", settings.search.base_url),
            "timeout": _settings_overrides["search"].get("timeout", settings.search.timeout),
            "max_results": _settings_overrides["search"].get("max_results", settings.search.max_results),
            "categories": _settings_overrides["search"].get("categories", settings.search.categories),
            "language": _settings_overrides["search"].get("language", settings.search.language),
        },
        "crawl": {
            "provider": settings.crawl.provider,
            "max_concurrent": _settings_overrides["crawl"].get("max_concurrent", settings.crawl.max_concurrent),
            "timeout": _settings_overrides["crawl"].get("timeout", settings.crawl.timeout),
            "max_content_length": _settings_overrides["crawl"].get("max_content_length", settings.crawl.max_content_length),
        },
        "agent": {
            "max_iterations": _settings_overrides["agent"].get("max_iterations", settings.agent.max_iterations),
            "min_sources": _settings_overrides["agent"].get("min_sources", settings.agent.min_sources),
            "max_sources": _settings_overrides["agent"].get("max_sources", settings.agent.max_sources),
            "coverage_threshold": _settings_overrides["agent"].get("coverage_threshold", settings.agent.coverage_threshold),
        },
        "user": _settings_overrides["user"],
        "version": settings.version,
        "environment": settings.environment,
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/", response_model=SystemSettingsResponse)
async def get_all_settings():
    """
    Get all current settings.
    
    Returns the merged settings from config file and runtime overrides.
    """
    merged = _get_merged_settings()
    
    return SystemSettingsResponse(
        llm=LLMSettings(
            provider=merged["llm"]["provider"],
            base_url=merged["llm"]["base_url"],
            temperature=merged["llm"]["temperature"],
            max_tokens=merged["llm"]["max_tokens"],
            timeout=merged["llm"]["timeout"],
            models=LLMModelsConfig(**merged["llm"]["models"])
        ),
        search=SearchSettings(
            provider=merged["search"]["provider"],
            base_url=merged["search"]["base_url"],
            timeout=merged["search"]["timeout"],
            max_results=merged["search"]["max_results"],
            categories=merged["search"]["categories"],
            language=merged["search"]["language"]
        ),
        crawl=CrawlSettings(
            max_concurrent=merged["crawl"]["max_concurrent"],
            timeout=merged["crawl"]["timeout"],
            max_content_length=merged["crawl"]["max_content_length"]
        ),
        agent=AgentSettings(
            max_iterations=merged["agent"]["max_iterations"],
            min_sources=merged["agent"]["min_sources"],
            max_sources=merged["agent"]["max_sources"],
            coverage_threshold=merged["agent"]["coverage_threshold"]
        ),
        user=UserPreferences(**merged["user"]),
        version=merged["version"],
        environment=merged["environment"]
    )


@router.get("/llm/models", response_model=list[LLMModelInfo])
async def get_available_models():
    """
    Get list of available LLM models from Ollama.
    
    Returns all models currently available for use.
    """
    settings = get_settings()
    
    try:
        client = _get_http_client()
        response = await client.get(f"{settings.llm.base_url}/api/tags")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama returned status {response.status_code}"
            )
        
        data = response.json()
        models = []
        
        for model in data.get("models", []):
            # Parse model details
            details = model.get("details", {})
            models.append(LLMModelInfo(
                name=model.get("name", ""),
                size=_format_size(model.get("size", 0)),
                modified_at=model.get("modified_at"),
                parameter_size=details.get("parameter_size"),
                quantization=details.get("quantization_level"),
                family=details.get("family")
            ))
        
        return models
            
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama. Is it running?"
        )
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/llm")
async def update_llm_settings(request: UpdateLLMSettingsRequest):
    """
    Update LLM settings.
    
    Changes are applied immediately and persist until server restart.
    """
    updates = request.model_dump(exclude_none=True)
    
    if "models" in updates:
        if "models" not in _settings_overrides["llm"]:
            _settings_overrides["llm"]["models"] = {}
        _settings_overrides["llm"]["models"].update(updates["models"])
        del updates["models"]
    
    _settings_overrides["llm"].update(updates)

    # Propagate to global config so all code sees the change
    all_llm = dict(_settings_overrides["llm"])
    apply_runtime_overrides("llm", all_llm)
    
    logger.info(f"Updated LLM settings: {updates}")
    
    return {"status": "updated", "updated_fields": list(request.model_dump(exclude_none=True).keys())}


@router.put("/search")
async def update_search_settings(request: UpdateSearchSettingsRequest):
    """Update search settings."""
    updates = request.model_dump(exclude_none=True)
    _settings_overrides["search"].update(updates)
    apply_runtime_overrides("search", updates)
    
    logger.info(f"Updated search settings: {updates}")
    
    return {"status": "updated", "updated_fields": list(updates.keys())}


@router.put("/agent")
async def update_agent_settings(request: UpdateAgentSettingsRequest):
    """Update agent behavior settings."""
    updates = request.model_dump(exclude_none=True)
    _settings_overrides["agent"].update(updates)
    apply_runtime_overrides("agent", updates)
    
    logger.info(f"Updated agent settings: {updates}")
    
    return {"status": "updated", "updated_fields": list(updates.keys())}


@router.put("/user")
async def update_user_preferences(request: UpdateUserPreferencesRequest):
    """Update user preferences."""
    updates = request.model_dump(exclude_none=True)
    _settings_overrides["user"].update(updates)
    
    logger.info(f"Updated user preferences: {updates}")
    
    return {"status": "updated", "updated_fields": list(updates.keys())}


@router.get("/status", response_model=AllServicesStatusResponse)
async def get_services_status():
    """
    Get status of all required services.
    
    Checks Ollama and SearXNG connectivity and returns their status.
    """
    settings = get_settings()
    
    # Check Ollama — get_settings() now reflects runtime overrides
    ollama_status = await _check_ollama_status(settings.llm.base_url)
    
    # Check SearXNG
    searxng_status = await _check_searxng_status(settings.search.base_url)
    
    # Determine overall status
    if ollama_status.status == "online" and searxng_status.status == "online":
        overall = "healthy"
    elif ollama_status.status == "offline" and searxng_status.status == "offline":
        overall = "unhealthy"
    else:
        overall = "degraded"
    
    return AllServicesStatusResponse(
        ollama=ollama_status,
        searxng=searxng_status,
        overall=overall
    )


@router.post("/test-connection")
async def test_service_connection(
    service: str,
    url: Optional[str] = None
):
    """
    Test connection to a specific service.
    
    Useful for validating new URLs before saving.
    """
    settings = get_settings()
    
    if service == "ollama":
        test_url = url or settings.llm.base_url
        return await _check_ollama_status(test_url)
    elif service == "searxng":
        test_url = url or settings.search.base_url
        return await _check_searxng_status(test_url)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")


@router.post("/reset")
async def reset_settings(section: Optional[str] = None):
    """
    Reset settings to defaults.
    
    If section is provided, only resets that section.
    Otherwise resets all settings.
    """
    global _settings_overrides
    
    if section:
        if section in _settings_overrides:
            if section == "user":
                _settings_overrides[section] = {
                    "username": "Guest Researcher",
                    "user_title": "Pro Plan",
                    "language": "English",
                    "default_research_mode": "balanced",
                    "default_profile": "general",
                    "enable_suggestions": True,
                    "enable_verification": True,
                    "theme": "diogenes"
                }
            else:
                _settings_overrides[section] = {}
            # Clear global config cache so get_settings() reloads without overrides
            clear_settings_cache()
            return {"status": "reset", "section": section}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown section: {section}")
    else:
        _settings_overrides = {
            "llm": {},
            "search": {},
            "crawl": {},
            "agent": {},
            "user": {
                "username": "Guest Researcher",
                "user_title": "Pro Plan",
                "language": "English",
                "default_research_mode": "balanced",
                "default_profile": "general",
                "enable_suggestions": True,
                "enable_verification": True,
                "theme": "diogenes"
            }
        }
        clear_settings_cache()
        return {"status": "reset", "section": "all"}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    if size_bytes == 0:
        return "Unknown"
    
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    
    return f"{size_bytes:.1f} TB"


async def _check_ollama_status(base_url: str) -> ServiceStatusResponse:
    """Check Ollama service status."""
    import time
    start = time.time()
    
    try:
        client = _get_http_client()
        response = await client.get(f"{base_url}/api/tags")
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            return ServiceStatusResponse(
                name="ollama",
                status="online",
                latency_ms=round(latency, 2),
                details={
                    "models_count": len(models),
                    "models": [m.get("name") for m in models[:5]]
                }
            )
        else:
            return ServiceStatusResponse(
                name="ollama",
                status="degraded",
                latency_ms=round(latency, 2),
                error=f"HTTP {response.status_code}"
            )
                
    except httpx.ConnectError:
        return ServiceStatusResponse(
            name="ollama",
            status="offline",
            error="Cannot connect to Ollama"
        )
    except Exception as e:
        return ServiceStatusResponse(
            name="ollama",
            status="offline",
            error=str(e)
        )


async def _check_searxng_status(base_url: str) -> ServiceStatusResponse:
    """Check SearXNG service status."""
    import time
    start = time.time()
    
    try:
        client = _get_http_client()
        # Try health endpoint first
        try:
            response = await client.get(f"{base_url}/healthz")
            if response.status_code == 200:
                latency = (time.time() - start) * 1000
                return ServiceStatusResponse(
                    name="searxng",
                    status="online",
                    latency_ms=round(latency, 2)
                )
        except:
            pass
        
        # Fallback to main page
        response = await client.get(f"{base_url}/")
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            return ServiceStatusResponse(
                name="searxng",
                status="online",
                latency_ms=round(latency, 2)
            )
        else:
            return ServiceStatusResponse(
                name="searxng",
                status="degraded",
                latency_ms=round(latency, 2),
                error=f"HTTP {response.status_code}"
            )
                
    except httpx.ConnectError:
        return ServiceStatusResponse(
            name="searxng",
            status="offline",
            error="Cannot connect to SearXNG"
        )
    except Exception as e:
        return ServiceStatusResponse(
            name="searxng",
            status="offline",
            error=str(e)
        )
