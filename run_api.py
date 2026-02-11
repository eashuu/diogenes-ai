"""
Run API server without hot reload for stable testing.
"""

import os
import uvicorn
from src.config import get_settings


def _resolve_workers(settings) -> int:
    """Determine the number of Uvicorn workers.

    Priority:
    1. ``DIOGENES_WORKERS`` env-var (legacy, for backwards compat)
    2. ``settings.api.workers`` config value
    3. Auto-detect in production: min(cpu_count, 4)
    4. Default: 1
    """
    explicit = os.environ.get("DIOGENES_WORKERS")
    if explicit is not None:
        return max(int(explicit), 1)

    configured = settings.api.workers
    if configured and configured > 0:
        return configured

    if settings.environment == "production":
        import multiprocessing
        return min(multiprocessing.cpu_count(), 4)

    return 1


if __name__ == "__main__":
    settings = get_settings()
    workers = _resolve_workers(settings)
    
    print(f"Starting Diogenes API on {settings.api.host}:{settings.api.port}")
    print(f"Workers: {workers} | Hot reload DISABLED for stability")
    print("Press CTRL+C to stop")
    print("-" * 60)
    
    uvicorn.run(
        "src.api.app:app",
        host=settings.api.host,
        port=settings.api.port,
        workers=workers,
        reload=False,  # Disable hot reload
        log_level="info"
    )
