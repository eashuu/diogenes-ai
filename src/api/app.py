"""
FastAPI Application.

Main entry point for the Diogenes Research API.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

import httpx

from src.config import get_settings
from src.utils.logging import setup_logging, get_logger
from src.utils.exceptions import DiogenesError
from src.api.routes import research_router, health_router, memory_router, settings_router


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    setup_logging(level=settings.logging.level)
    
    logger.info(
        f"Starting Diogenes API v{settings.version} "
        f"({settings.environment})"
    )
    
    # Warn if binding to non-localhost — network exposure
    if settings.api.host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning(
            f"Binding to {settings.api.host} exposes Diogenes to your network. "
            "Set DIOGENES_API_HOST=127.0.0.1 for localhost-only access."
        )
    
    # Warn if API key protection is off and binding externally
    if not settings.api.require_api_key and settings.api.host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning(
            "No API key required while bound to network. "
            "Set DIOGENES_API_REQUIRE_API_KEY=true and DIOGENES_API_API_KEY=<secret>."
        )
    
    # Initialize services (warmup)
    try:
        from src.core.agent.nodes import get_services
        services = get_services()
        logger.info("Services initialized")
    except Exception as e:
        logger.warning(f"Service warmup failed: {e}")
    
    # Startup health checks — validate service URLs and model availability
    await _startup_health_checks(settings)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Diogenes API")


def _warn_plaintext_http(service_label: str, url: str) -> None:
    """Log a warning if a non-localhost service URL uses plain HTTP."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme == "http" and not is_localhost:
        logger.warning(
            f"{service_label} is using plaintext HTTP ({url}). "
            "Consider using HTTPS for non-localhost services to protect data in transit. "
            "Set verify_ssl=false in config if using self-signed certificates."
        )


async def _startup_health_checks(settings) -> None:
    """
    Validate external service URLs and model availability at startup.

    Checks:
    - Ollama API reachable at configured llm.base_url
    - Required LLM models are pulled in Ollama
    - SearXNG API reachable at configured search.base_url
    - Warns if non-localhost services use plaintext HTTP

    All failures are logged as warnings — the app still starts so that
    operators can fix services without a chicken-and-egg problem.
    """
    timeout = httpx.Timeout(10.0)

    # --- Ollama check ---
    ollama_url = settings.llm.base_url
    ollama_ok = False

    # Warn if non-localhost services use plaintext HTTP
    _warn_plaintext_http("Ollama (llm.base_url)", ollama_url)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            resp.raise_for_status()
            ollama_ok = True
            logger.info(f"Ollama reachable at {ollama_url}")

            # Check required models
            available_models = {
                m.get("name", "") for m in resp.json().get("models", [])
            }
            # Normalise names: Ollama tags may include :latest
            available_base = set()
            for name in available_models:
                available_base.add(name)
                if ":" in name:
                    available_base.add(name.split(":")[0])

            models_cfg = settings.llm.models
            required = {
                "planner": models_cfg.planner,
                "extractor": models_cfg.extractor,
                "synthesizer": models_cfg.synthesizer,
                "reflector": models_cfg.reflector,
            }
            for role, model_name in required.items():
                if model_name not in available_base:
                    logger.warning(
                        f"LLM model '{model_name}' (role={role}) not found in Ollama. "
                        f"Pull it with: ollama pull {model_name}"
                    )
                else:
                    logger.info(f"LLM model '{model_name}' ({role}) available")
    except httpx.ConnectError:
        logger.warning(
            f"Cannot connect to Ollama at {ollama_url}. "
            "LLM features will fail until Ollama is started."
        )
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")

    # --- SearXNG check ---
    searxng_url = settings.search.base_url
    _warn_plaintext_http("SearXNG (search.base_url)", searxng_url)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # SearXNG exposes a simple root or /healthz — try root
            resp = await client.get(f"{searxng_url}/healthz")
            if resp.status_code < 500:
                logger.info(f"SearXNG reachable at {searxng_url}")
            else:
                # Try root as fallback (some SearXNG versions)
                resp2 = await client.get(searxng_url)
                if resp2.status_code < 500:
                    logger.info(f"SearXNG reachable at {searxng_url}")
                else:
                    logger.warning(
                        f"SearXNG at {searxng_url} returned HTTP {resp.status_code}. "
                        "Search may not work correctly."
                    )
    except httpx.ConnectError:
        logger.warning(
            f"Cannot connect to SearXNG at {searxng_url}. "
            "Search features will fail until SearXNG is started."
        )
    except Exception as e:
        logger.warning(f"SearXNG health check failed: {e}")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Diogenes Research API",
        description="""
        AI-powered research assistant that searches, crawls, and synthesizes 
        information from the web to answer complex queries.
        
        ## Features
        
        - **Multi-source search**: Searches across multiple search engines via SearXNG
        - **Intelligent crawling**: Extracts clean content from web pages
        - **Quality scoring**: Ranks sources by authority, freshness, and relevance
        - **Cited answers**: Provides comprehensive answers with source citations
        - **Streaming**: Real-time progress updates via Server-Sent Events
        
        ## Endpoints
        
        - `POST /api/v1/research/` - Start a research query (blocking)
        - `POST /api/v1/research/stream` - Start research with SSE streaming
        - `GET /api/v1/research/{session_id}` - Get research results
        - `GET /api/v1/health/` - Health check
        """,
        version=settings.version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan
    )
    
    # CORS middleware — block wildcard origins in production
    cors_origins = settings.api.cors_origins
    if settings.environment == "production" and "*" in cors_origins:
        logger.warning(
            "CORS allow_origins=['*'] is insecure in production. "
            "Falling back to empty origins list. Set specific origins in config."
        )
        cors_origins = []
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start_time = datetime.now()
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        response.headers["X-Process-Time-Ms"] = str(int(process_time))
        return response
    
    # Optional API key middleware (FOSS-local-first: off by default)
    if settings.api.require_api_key:
        expected_key = settings.api.api_key
        if not expected_key:
            logger.error(
                "DIOGENES_API_REQUIRE_API_KEY=true but DIOGENES_API_API_KEY is empty. "
                "API key enforcement disabled."
            )
        else:
            # Exempt paths that should always be accessible
            _EXEMPT_PATHS = frozenset({"/", "/docs", "/redoc", "/openapi.json", "/health/", "/health"})
            
            @app.middleware("http")
            async def api_key_guard(request: Request, call_next):
                if request.url.path in _EXEMPT_PATHS:
                    return await call_next(request)
                
                provided_key = request.headers.get("X-API-Key", "")
                if provided_key != expected_key:
                    return JSONResponse(
                        status_code=HTTP_401_UNAUTHORIZED,
                        content={
                            "error": "Unauthorized",
                            "message": "Invalid or missing API key. Provide X-API-Key header.",
                        }
                    )
                return await call_next(request)
            
            logger.info("API key guard enabled — X-API-Key header required for protected endpoints")
    
    # Prometheus metrics middleware
    try:
        from src.api.metrics import PrometheusMiddleware, set_app_info
        app.add_middleware(PrometheusMiddleware)
        set_app_info(version=settings.version, environment=settings.environment)
        logger.info("Prometheus metrics enabled at /health/metrics")
    except Exception as e:
        logger.warning(f"Prometheus metrics not available: {e}")

    # Exception handlers
    @app.exception_handler(DiogenesError)
    async def diogenes_error_handler(request: Request, exc: DiogenesError):
        logger.error(f"DiogenesError: {exc}")
        is_production = settings.environment == "production"
        return JSONResponse(
            status_code=500,
            content={
                "error": exc.code,
                "message": exc.message if not is_production else "An error occurred",
                "recoverable": exc.recoverable,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Include routers — unified V1 API
    app.include_router(research_router, prefix="/api/v1")
    app.include_router(health_router)  # health at /health/
    app.include_router(memory_router, prefix="/api/v1")  # memory at /api/v1/memory
    app.include_router(settings_router, prefix="/api/v1")  # settings at /api/v1/settings
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Diogenes Research API",
            "version": settings.version,
            "environment": settings.environment,
            "docs": "/docs" if settings.environment != "production" else None
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import sys
    import uvicorn
    
    # Fix Windows asyncio event loop for Playwright compatibility
    if sys.platform == 'win32':
        import asyncio
        # Try to use WindowsSelectorEventLoop for Playwright
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Using WindowsSelectorEventLoop for Playwright compatibility")
        except AttributeError:
            logger.warning("WindowsSelectorEventLoop not available, using default")
    
    settings = get_settings()
    
    workers = settings.api.workers
    if workers <= 0 and settings.environment == "production":
        import multiprocessing
        workers = min(multiprocessing.cpu_count(), 4)
    else:
        workers = max(workers, 1)
    
    uvicorn.run(
        "src.api.app:app",
        host=settings.api.host,
        port=settings.api.port,
        workers=workers,
        reload=settings.environment == "development" and workers == 1,
        log_level="info"
    )
