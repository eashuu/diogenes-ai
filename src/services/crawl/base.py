"""
Abstract base class for crawl services.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.services.crawl.models import (
    CrawlConfig,
    CrawlResult,
    CrawlBatchResult,
    ExtractMode,
)


class CrawlService(ABC):
    """
    Abstract interface for web crawling services.
    
    Implementations must provide async crawling functionality
    with support for JavaScript rendering and content extraction.
    """
    
    @abstractmethod
    async def crawl(
        self,
        url: str,
        config: Optional[CrawlConfig] = None,
    ) -> CrawlResult:
        """
        Crawl a single URL.
        
        Args:
            url: URL to crawl
            config: Optional crawl configuration
            
        Returns:
            CrawlResult with extracted content
            
        Raises:
            CrawlError: If crawl fails
            CrawlTimeoutError: If crawl times out
        """
        pass
    
    @abstractmethod
    async def crawl_many(
        self,
        urls: list[str],
        config: Optional[CrawlConfig] = None,
        max_concurrent: int = 5,
    ) -> CrawlBatchResult:
        """
        Crawl multiple URLs in parallel.
        
        Args:
            urls: List of URLs to crawl
            config: Optional crawl configuration
            max_concurrent: Maximum concurrent crawls
            
        Returns:
            CrawlBatchResult with all results
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the crawl service is available.
        
        Returns:
            True if service is healthy
        """
        pass
    
    async def crawl_with_retry(
        self,
        url: str,
        config: Optional[CrawlConfig] = None,
        max_retries: int = 2,
    ) -> CrawlResult:
        """
        Crawl with automatic retry on failure.
        
        Default implementation uses the retry utility.
        """
        from src.utils.retry import RetryConfig, retry_async
        from src.utils.exceptions import CrawlError
        
        retry_config = RetryConfig(
            max_attempts=max_retries,
            base_delay=1.0,
            exceptions=(CrawlError,),
        )
        
        return await retry_async(
            self.crawl,
            url,
            crawl_config=config,
            retry_config=retry_config,
        )
