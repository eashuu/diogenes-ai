"""
Rate Limiting Middleware.

Simple in-memory sliding-window rate limiter for the API.
"""

import time
from collections import defaultdict
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    In-memory sliding-window rate limiter.

    Tracks request timestamps per client IP and enforces a maximum
    number of requests within a given window.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if a request from *client_id* is allowed.

        Returns:
            (allowed, remaining) — whether the request is allowed and the
            remaining quota within the current window.
        """
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Prune old timestamps
        timestamps = self._requests[client_id]
        self._requests[client_id] = [t for t in timestamps if t > window_start]

        remaining = self.max_requests - len(self._requests[client_id])

        if remaining <= 0:
            return False, 0

        self._requests[client_id].append(now)
        return True, remaining - 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that enforces per-IP rate limiting.

    Exempt paths (health checks) are not rate-limited.
    """

    _EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip rate-limiting for exempt paths
        if any(path.startswith(p) for p in self._EXEMPT_PREFIXES):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        allowed, remaining = self.limiter.is_allowed(client_ip)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "TooManyRequests",
                    "message": "Rate limit exceeded. Please try again later.",
                },
                headers={
                    "Retry-After": str(self.limiter.window_seconds),
                    "X-RateLimit-Limit": str(self.limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every response.

    Based on OWASP recommendations.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        return response
