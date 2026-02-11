"""Search Service - SearXNG and academic source integration."""
from .base import SearchService
from .searxng import SearXNGService
from .models import SearchResult, SearchQuery
from .arxiv import ArxivService, ArxivPaper, ArxivSearchResult, ArxivAuthor

__all__ = [
    "SearchService", 
    "SearXNGService", 
    "SearchResult", 
    "SearchQuery",
    "ArxivService",
    "ArxivPaper",
    "ArxivSearchResult",
    "ArxivAuthor",
]
