"""API Routes."""
from src.api.routes.research_unified import router as research_router
from src.api.routes.health import router as health_router
from src.api.routes.memory import router as memory_router
from src.api.routes.settings import router as settings_router

__all__ = ["research_router", "health_router", "memory_router", "settings_router"]
