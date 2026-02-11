"""
Health Check Routes.

Provides health and readiness endpoints for monitoring.
"""

import asyncio
import time
from datetime import datetime

from fastapi import APIRouter
import httpx

from src.config import get_settings
from src.utils.logging import get_logger
from src.api.schemas import HealthResponse, ServiceHealth
from src.services.search.searxng import SearXNGService
from src.services.llm.ollama import OllamaService


logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

# Reuse a single httpx client for all health checks (connection pooling)
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Get or lazily create the shared httpx client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=5.0)
    return _http_client


async def _check_searxng() -> ServiceHealth:
    """Check SearXNG health."""
    settings = get_settings()
    start = time.time()
    
    try:
        client = _get_http_client()
        response = await client.get(f"{settings.search.base_url}/")
        latency = (time.time() - start) * 1000
        
        return ServiceHealth(
            name="searxng",
            healthy=response.status_code == 200,
            latency_ms=latency
        )
    except Exception as e:
        return ServiceHealth(
            name="searxng",
            healthy=False,
            error=str(e)
        )


async def _check_ollama() -> ServiceHealth:
    """Check Ollama health."""
    settings = get_settings()
    start = time.time()
    
    try:
        client = _get_http_client()
        response = await client.get(f"{settings.llm.base_url}/api/tags")
        latency = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # Check if our required model is available
            required_model = settings.llm.models.synthesizer
            has_model = any(
                required_model in name 
                for name in model_names
            )
            
            return ServiceHealth(
                name="ollama",
                healthy=has_model,
                latency_ms=latency,
                error=None if has_model else f"Model {required_model} not found"
            )
        
        return ServiceHealth(
            name="ollama",
            healthy=False,
            latency_ms=latency,
            error=f"HTTP {response.status_code}"
        )
        
    except Exception as e:
        return ServiceHealth(
            name="ollama",
            healthy=False,
            error=str(e)
        )


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check.
    
    Checks all dependent services and returns overall status.
    """
    settings = get_settings()
    
    # Check all services in parallel
    searxng_health, ollama_health = await asyncio.gather(
        _check_searxng(),
        _check_ollama()
    )
    
    services = [searxng_health, ollama_health]
    
    # Overall status
    all_healthy = all(s.healthy for s in services)
    any_healthy = any(s.healthy for s in services)
    
    if all_healthy:
        status = "healthy"
    elif any_healthy:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        version=settings.version,
        services=services,
        timestamp=datetime.utcnow()
    )


@router.get("/live")
async def liveness():
    """
    Kubernetes liveness probe.
    
    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """
    Kubernetes readiness probe.
    
    Returns 200 if the application can serve requests.
    Checks critical dependencies.
    """
    settings = get_settings()
    
    # Quick check of critical services
    searxng_health = await _check_searxng()
    ollama_health = await _check_ollama()
    
    if not searxng_health.healthy:
        return {
            "status": "not_ready",
            "reason": "SearXNG unavailable"
        }
    
    if not ollama_health.healthy:
        return {
            "status": "not_ready", 
            "reason": "Ollama unavailable"
        }
    
    return {"status": "ready"}


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.
    """
    from src.api.metrics import metrics_response
    return metrics_response()
