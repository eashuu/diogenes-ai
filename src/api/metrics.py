"""
Prometheus metrics for Diogenes API.

Exposes request counters, latency histograms, and research-specific
gauges that can be scraped by Prometheus at ``/health/metrics``.

Usage in ``app.py``::

    from src.api.metrics import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)
"""

import time
from typing import Callable

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.utils.logging import get_logger


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "diogenes_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "diogenes_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

RESEARCH_IN_PROGRESS = Gauge(
    "diogenes_research_in_progress",
    "Number of research queries currently being processed",
)

RESEARCH_TOTAL = Counter(
    "diogenes_research_total",
    "Total research queries",
    ["mode", "profile", "status"],
)

RESEARCH_DURATION = Histogram(
    "diogenes_research_duration_seconds",
    "Research query duration in seconds",
    ["mode"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

APP_INFO = Info(
    "diogenes",
    "Diogenes application information",
)


def set_app_info(version: str, environment: str) -> None:
    """Set application info metric (call once at startup)."""
    APP_INFO.info({"version": version, "environment": environment})


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def _normalise_path(path: str) -> str:
    """
    Collapse path parameters to reduce cardinality.

    ``/api/v1/research/abc-123`` → ``/api/v1/research/{id}``
    """
    import re
    # UUIDs
    path = re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "{id}",
        path,
    )
    # Generic numeric IDs
    path = re.sub(r"/\d+", "/{id}", path)
    return path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that records Prometheus metrics per request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = _normalise_path(request.url.path)

        # Skip metrics endpoint itself to avoid recursion noise
        if path.endswith("/metrics"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        status = str(response.status_code)
        REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

        return response


# ---------------------------------------------------------------------------
# /metrics endpoint helper
# ---------------------------------------------------------------------------

def metrics_response() -> Response:
    """Generate a Prometheus-format ``/metrics`` response."""
    body = generate_latest(REGISTRY)
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
