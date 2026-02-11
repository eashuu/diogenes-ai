"""
Search service models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal
from enum import Enum


class TimeRange(str, Enum):
    """Time range filter for search."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL = "all"


@dataclass
class SearchQuery:
    """Represents a search query with options."""
    
    query: str
    num_results: int = 10
    categories: list[str] = field(default_factory=lambda: ["general"])
    language: str = "en-US"
    time_range: TimeRange = TimeRange.ALL
    safe_search: bool = True
    
    def __hash__(self) -> int:
        """Make hashable for caching."""
        return hash((
            self.query,
            self.num_results,
            tuple(self.categories),
            self.language,
            self.time_range,
        ))


@dataclass
class SearchResult:
    """Represents a single search result."""
    
    url: str
    title: str
    snippet: str
    score: float = 0.0
    engine: Optional[str] = None
    category: Optional[str] = None
    published_date: Optional[datetime] = None
    
    # Metadata extracted from URL
    domain: str = ""
    favicon_url: str = ""
    
    def __post_init__(self):
        """Extract domain and favicon from URL."""
        if not self.domain and self.url:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            self.domain = parsed.netloc
            self.favicon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
    
    def __hash__(self) -> int:
        return hash(self.url)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, SearchResult):
            return False
        return self.url == other.url


@dataclass
class SearchResponse:
    """Response from a search operation."""
    
    query: SearchQuery
    results: list[SearchResult]
    total_results: int = 0
    search_time: float = 0.0
    cached: bool = False
    
    @property
    def has_results(self) -> bool:
        return len(self.results) > 0
    
    def get_urls(self) -> list[str]:
        """Get all URLs from results."""
        return [r.url for r in self.results]
    
    def deduplicate(self) -> "SearchResponse":
        """Remove duplicate URLs, keeping highest-scored."""
        seen: dict[str, SearchResult] = {}
        for result in self.results:
            if result.url not in seen or result.score > seen[result.url].score:
                seen[result.url] = result
        
        return SearchResponse(
            query=self.query,
            results=list(seen.values()),
            total_results=len(seen),
            search_time=self.search_time,
            cached=self.cached,
        )
