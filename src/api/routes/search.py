"""
Image & Video Search API Routes.

Provides specialized search endpoints for image and video results
via SearXNG's category system.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.search.searxng import SearXNGService
from src.services.search.models import TimeRange
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

_search_service: SearXNGService | None = None


def _get_search_service() -> SearXNGService:
    global _search_service
    if _search_service is None:
        _search_service = SearXNGService()
    return _search_service


# =============================================================================
# SCHEMAS
# =============================================================================


class ImageResult(BaseModel):
    title: str = ""
    url: str = ""
    thumbnail_url: str = ""
    source_url: str = ""
    width: int | None = None
    height: int | None = None
    engine: str | None = None


class VideoResult(BaseModel):
    title: str = ""
    url: str = ""
    thumbnail_url: str = ""
    duration: str | None = None
    source: str | None = None
    engine: str | None = None
    published_date: str | None = None


class ImageSearchResponse(BaseModel):
    query: str
    images: list[ImageResult]
    total: int


class VideoSearchResponse(BaseModel):
    query: str
    videos: list[VideoResult]
    total: int


class SocialResult(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str | None = None
    published_date: str | None = None


class SocialSearchResponse(BaseModel):
    query: str
    results: list[SocialResult]
    total: int


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/images", response_model=ImageSearchResponse)
async def search_images(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    num_results: int = Query(default=20, ge=1, le=100),
    time_range: str = Query(default="all", pattern="^(day|week|month|year|all)$"),
):
    """Search for images via SearXNG."""
    service = _get_search_service()

    try:
        response = await service.search(
            query=q,
            num_results=num_results,
            categories=["images"],
            time_range=TimeRange(time_range),
        )
    except Exception as e:
        raise HTTPException(502, f"Image search failed: {e}")

    images = []
    for r in response.results:
        images.append(
            ImageResult(
                title=r.title,
                url=r.url,
                thumbnail_url=getattr(r, "thumbnail_url", "") or r.url,
                source_url=r.url,
                engine=r.engine,
            )
        )

    return ImageSearchResponse(query=q, images=images, total=len(images))


@router.get("/videos", response_model=VideoSearchResponse)
async def search_videos(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    num_results: int = Query(default=20, ge=1, le=100),
    time_range: str = Query(default="all", pattern="^(day|week|month|year|all)$"),
):
    """Search for videos via SearXNG."""
    service = _get_search_service()

    try:
        response = await service.search(
            query=q,
            num_results=num_results,
            categories=["videos"],
            time_range=TimeRange(time_range),
        )
    except Exception as e:
        raise HTTPException(502, f"Video search failed: {e}")

    videos = []
    for r in response.results:
        videos.append(
            VideoResult(
                title=r.title,
                url=r.url,
                thumbnail_url=getattr(r, "thumbnail_url", "") or "",
                source=r.engine,
                engine=r.engine,
                published_date=r.published_date.isoformat() if r.published_date else None,
            )
        )

    return VideoSearchResponse(query=q, videos=videos, total=len(videos))


@router.get("/social", response_model=SocialSearchResponse)
async def search_social(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    num_results: int = Query(default=20, ge=1, le=100),
    time_range: str = Query(default="all", pattern="^(day|week|month|year|all)$"),
):
    """Search social media (Reddit, forums) via SearXNG."""
    service = _get_search_service()

    try:
        response = await service.search(
            query=f"{q} site:reddit.com OR site:news.ycombinator.com",
            num_results=num_results,
            categories=["general", "social media"],
            time_range=TimeRange(time_range),
        )
    except Exception as e:
        raise HTTPException(502, f"Social search failed: {e}")

    results = []
    for r in response.results:
        results.append(
            SocialResult(
                title=r.title,
                url=r.url,
                snippet=r.snippet or "",
                source=r.engine,
                published_date=r.published_date.isoformat() if r.published_date else None,
            )
        )

    return SocialSearchResponse(query=q, results=results, total=len(results))
