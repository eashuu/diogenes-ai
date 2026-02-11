"""
Abstract base class for search services.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.services.search.models import SearchQuery, SearchResponse, SearchResult, TimeRange


class SearchService(ABC):
    """
    Abstract interface for search providers.
    
    Implementations must provide async search functionality.
    All implementations should support caching and retry logic.
    """
    
    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        categories: Optional[list[str]] = None,
        time_range: TimeRange = TimeRange.ALL,
        language: str = "en-US",
    ) -> SearchResponse:
        """
        Execute a search query.
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return
            categories: Search categories (e.g., ["general", "news"])
            time_range: Time range filter
            language: Language code (e.g., "en-US")
            
        Returns:
            SearchResponse containing results
            
        Raises:
            SearchError: If search fails
            SearchTimeoutError: If search times out
        """
        pass
    
    @abstractmethod
    async def search_multiple(
        self,
        queries: list[str],
        num_results_per_query: int = 10,
        deduplicate: bool = True,
    ) -> SearchResponse:
        """
        Execute multiple search queries and combine results.
        
        Args:
            queries: List of search queries
            num_results_per_query: Max results per query
            deduplicate: Whether to remove duplicate URLs
            
        Returns:
            Combined SearchResponse
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the search service is available.
        
        Returns:
            True if service is healthy
        """
        pass
