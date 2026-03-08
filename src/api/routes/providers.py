"""
LLM Provider management API routes.

Lists available providers, tests connectivity, and manages provider selection.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import get_settings, apply_runtime_overrides
from src.services.llm.registry import (
    get_llm_service,
    list_available_providers,
    clear_provider_cache,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/providers", tags=["providers"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ProviderInfo(BaseModel):
    name: str
    configured: bool = False
    models: list[str] = Field(default_factory=list)
    healthy: bool = False


class ProviderListResponse(BaseModel):
    active_provider: str
    providers: list[ProviderInfo]


class SetProviderRequest(BaseModel):
    provider: str
    default_model: str | None = None


class ProviderHealthResponse(BaseModel):
    provider: str
    healthy: bool
    models: list[str] = Field(default_factory=list)
    error: str | None = None


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("", response_model=ProviderListResponse)
async def list_providers():
    """List all providers and their configuration status."""
    settings = get_settings()
    active = settings.llm.provider
    available = list_available_providers()

    provider_infos = []
    for name in ("ollama", "openai", "anthropic", "groq", "gemini"):
        provider_infos.append(
            ProviderInfo(
                name=name,
                configured=name in available,
            )
        )

    return ProviderListResponse(active_provider=active, providers=provider_infos)


@router.post("/active", response_model=dict)
async def set_active_provider(req: SetProviderRequest):
    """Switch the active LLM provider."""
    valid = {"ollama", "openai", "anthropic", "groq", "gemini"}
    if req.provider not in valid:
        raise HTTPException(400, f"Unknown provider: {req.provider}")

    updates: dict = {"provider": req.provider}
    apply_runtime_overrides("llm", updates)
    clear_provider_cache()

    return {"status": "ok", "active_provider": req.provider}


@router.get("/{provider_name}/health", response_model=ProviderHealthResponse)
async def check_provider_health(provider_name: str):
    """Check connectivity & list models for a specific provider."""
    try:
        service = get_llm_service(provider=provider_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        return ProviderHealthResponse(
            provider=provider_name, healthy=False, error=str(e)
        )

    healthy = False
    models: list[str] = []
    error = None
    try:
        healthy = await service.health_check()
        if healthy:
            models = await service.list_models()
    except Exception as e:
        error = str(e)

    return ProviderHealthResponse(
        provider=provider_name,
        healthy=healthy,
        models=models[:50],  # Cap list size
        error=error,
    )


@router.get("/{provider_name}/models", response_model=list[str])
async def list_provider_models(provider_name: str):
    """List models available from a provider."""
    try:
        service = get_llm_service(provider=provider_name)
        return await service.list_models()
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Failed to list models from {provider_name}: {e}")
