"""
Discover Page API.

Returns trending/interesting topics and content for the Discover page,
similar to Perplexica's Discover feature.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.search.searxng import SearXNGService
from src.services.search.models import TimeRange
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/discover", tags=["discover"])

_search_service: SearXNGService | None = None


def _get_search_service() -> SearXNGService:
    global _search_service
    if _search_service is None:
        _search_service = SearXNGService()
    return _search_service


# =============================================================================
# SCHEMAS
# =============================================================================


class DiscoverItem(BaseModel):
    title: str
    url: str
    snippet: str = ""
    thumbnail_url: str | None = None
    source: str = ""
    category: str = "general"
    published_date: str | None = None


class DiscoverResponse(BaseModel):
    items: list[DiscoverItem]
    generated_at: str
    category: str


# =============================================================================
# Trending topic seeds by category
# =============================================================================

_DISCOVER_QUERIES = {
    "trending": [
        "trending technology news today",
        "latest science discoveries",
        "breaking news today world",
    ],
    "science": [
        "latest scientific discoveries 2025",
        "space exploration news",
        "climate research findings",
    ],
    "technology": [
        "AI news today",
        "latest software development tools",
        "cybersecurity news",
    ],
    "culture": [
        "trending books 2025",
        "notable art exhibitions",
        "music releases this week",
    ],
}


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("", response_model=DiscoverResponse)
async def get_discover_feed(
    category: str = Query(
        default="trending",
        pattern="^(trending|science|technology|culture)$",
    ),
    num_results: int = Query(default=15, ge=5, le=50),
):
    """
    Get a discover feed with trending content.

    The discover endpoint fetches fresh results from SearXNG
    using curated seed queries for the requested category.
    """
    service = _get_search_service()
    queries = _DISCOVER_QUERIES.get(category, _DISCOVER_QUERIES["trending"])

    all_items: list[DiscoverItem] = []
    seen_urls: set[str] = set()

    for query in queries:
        try:
            response = await service.search(
                query=query,
                num_results=num_results // len(queries) + 2,
                categories=["general", "news"],
                time_range=TimeRange.WEEK,
            )
            for r in response.results:
                if r.url in seen_urls:
                    continue
                seen_urls.add(r.url)
                all_items.append(
                    DiscoverItem(
                        title=r.title,
                        url=r.url,
                        snippet=r.snippet or "",
                        source=r.engine or "",
                        category=category,
                        published_date=r.published_date.isoformat() if r.published_date else None,
                    )
                )
        except Exception as e:
            logger.warning(f"Discover query failed for '{query}': {e}")

    return DiscoverResponse(
        items=all_items[:num_results],
        generated_at=datetime.utcnow().isoformat(),
        category=category,
    )
