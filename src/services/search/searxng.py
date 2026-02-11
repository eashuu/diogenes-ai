"""
SearXNG search service implementation.
"""

import asyncio
from typing import Optional
from datetime import datetime

import httpx

from src.config import get_settings
from src.services.search.base import SearchService
from src.services.search.models import (
    SearchQuery,
    SearchResult,
    SearchResponse,
    TimeRange,
)
from src.utils.exceptions import (
    SearchError,
    SearchTimeoutError,
    SearchConnectionError,
    NoSearchResultsError,
)
from src.utils.logging import get_logger
from src.utils.retry import with_retry, RetryConfig

logger = get_logger(__name__)


class SearXNGService(SearchService):
    """
    SearXNG search service implementation.
    
    Provides privacy-focused metasearch using a self-hosted SearXNG instance.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_results: Optional[int] = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.search.base_url
        self.timeout = timeout or settings.search.timeout
        self.max_results = max_results or settings.search.max_results
        self.default_categories = settings.search.categories
        self.default_language = settings.search.language
        self._verify_ssl = settings.search.verify_ssl
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": "DiogenesResearchBot/2.0",
                    "Accept": "application/json",
                },
                verify=self._verify_ssl,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _map_time_range(self, time_range: TimeRange) -> Optional[str]:
        """Map TimeRange enum to SearXNG parameter."""
        mapping = {
            TimeRange.DAY: "day",
            TimeRange.WEEK: "week",
            TimeRange.MONTH: "month",
            TimeRange.YEAR: "year",
            TimeRange.ALL: None,
        }
        return mapping.get(time_range)
    
    def _parse_result(self, raw: dict) -> SearchResult:
        """Parse a raw SearXNG result into SearchResult."""
        # Parse published date if available
        published_date = None
        if raw.get("publishedDate"):
            try:
                published_date = datetime.fromisoformat(
                    raw["publishedDate"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
        
        return SearchResult(
            url=raw.get("url", ""),
            title=raw.get("title", ""),
            snippet=raw.get("content", ""),
            score=raw.get("score", 0.0),
            engine=raw.get("engine"),
            category=raw.get("category"),
            published_date=published_date,
        )
    
    @with_retry(max_attempts=3, base_delay=1.0)
    async def search(
        self,
        query: str,
        num_results: int = 10,
        categories: Optional[list[str]] = None,
        time_range: TimeRange = TimeRange.ALL,
        language: str = "en-US",
    ) -> SearchResponse:
        """
        Execute a search query against SearXNG.
        """
        import time
        start_time = time.time()
        
        search_query = SearchQuery(
            query=query,
            num_results=num_results,
            categories=categories or self.default_categories,
            language=language,
            time_range=time_range,
        )
        
        logger.debug(f"Searching SearXNG: '{query}'")
        
        # Build request parameters
        params = {
            "q": query,
            "format": "json",
            "categories": ",".join(search_query.categories),
            "language": language,
        }
        
        logger.info(f"SearXNG request params: {params}")
        
        # Add time range if specified
        time_range_param = self._map_time_range(time_range)
        if time_range_param:
            params["time_range"] = time_range_param
        
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/search",
                params=params,
            )
            response.raise_for_status()
            logger.info(f"SearXNG response: status={response.status_code}, size={len(response.content)} bytes")
            data = response.json()
            # Debug: log full response JSON to help diagnose empty-result cases
            logger.debug(f"SearXNG full response: {data}")
            logger.info(f"SearXNG results count: {len(data.get('results', []))}")
            
        except httpx.TimeoutException as e:
            logger.error(f"SearXNG timeout for query: {query}")
            raise SearchTimeoutError(query, self.timeout) from e
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to SearXNG at {self.base_url}")
            raise SearchConnectionError("SearXNG", str(e)) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"SearXNG HTTP error: {e.response.status_code}")
            raise SearchError(
                f"Search failed with status {e.response.status_code}",
                code="SEARCH_HTTP_ERROR",
            ) from e
        except Exception as e:
            logger.error(f"Unexpected search error: {e}")
            raise SearchError(str(e)) from e
        
        # Parse results
        raw_results = data.get("results", [])
        results = []
        seen_urls = set()
        
        for raw in raw_results:
            url = raw.get("url", "")
            if not url or url in seen_urls:
                continue
            
            seen_urls.add(url)
            result = self._parse_result(raw)
            results.append(result)
            
            if len(results) >= num_results:
                break
        
        search_time = time.time() - start_time
        
        logger.info(
            f"Search complete: '{query}' -> {len(results)} results in {search_time:.2f}s"
        )
        
        return SearchResponse(
            query=search_query,
            results=results,
            total_results=len(results),
            search_time=search_time,
            cached=False,
        )
    
    async def search_multiple(
        self,
        queries: list[str],
        num_results_per_query: int = 10,
        deduplicate: bool = True,
    ) -> SearchResponse:
        """
        Execute multiple search queries in parallel and combine results.
        """
        import time
        start_time = time.time()
        
        logger.info(f"Executing {len(queries)} parallel searches")
        
        # Execute searches in parallel
        tasks = [
            self.search(q, num_results=num_results_per_query)
            for q in queries
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_results: list[SearchResult] = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.warning(f"Search failed for query '{queries[i]}': {response}")
                continue
            all_results.extend(response.results)
        
        # Deduplicate if requested
        if deduplicate:
            seen: dict[str, SearchResult] = {}
            for result in all_results:
                if result.url not in seen or result.score > seen[result.url].score:
                    seen[result.url] = result
            all_results = list(seen.values())
        
        # Sort by score
        all_results.sort(key=lambda r: r.score, reverse=True)
        
        total_time = time.time() - start_time
        
        logger.info(
            f"Combined search complete: {len(queries)} queries -> "
            f"{len(all_results)} unique results in {total_time:.2f}s"
        )
        
        return SearchResponse(
            query=SearchQuery(query="; ".join(queries)),
            results=all_results,
            total_results=len(all_results),
            search_time=total_time,
            cached=False,
        )
    
    async def health_check(self) -> bool:
        """Check if SearXNG is available."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"SearXNG health check failed: {e}")
            return False
