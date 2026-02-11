"""
crawl4ai web crawling service implementation.

Implements Windows compatibility by running Playwright in a thread pool
with WindowsSelectorEventLoop when FastAPI uses ProactorEventLoop.
"""

import asyncio
import sys
from typing import Optional
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import functools

from src.config import get_settings
from src.services.crawl.base import CrawlService
from src.services.crawl.models import (
    CrawlConfig,
    CrawlResult,
    CrawlBatchResult,
    CrawlStatus,
    ExtractMode,
)
from src.utils.exceptions import (
    CrawlError,
    CrawlTimeoutError,
    CrawlBlockedError,
    CrawlContentError,
)
from src.utils.logging import get_logger
from src.utils.url_validation import validate_url_for_ssrf

logger = get_logger(__name__)

# Global thread pool for Windows Playwright compatibility
_PLAYWRIGHT_EXECUTOR: Optional[ThreadPoolExecutor] = None
_WINDOWS_WORKAROUND_ENABLED = False


def _init_playwright_executor():
    """Initialize thread pool executor for Windows Playwright compatibility."""
    global _PLAYWRIGHT_EXECUTOR, _WINDOWS_WORKAROUND_ENABLED
    
    if _PLAYWRIGHT_EXECUTOR is not None:
        # Already initialized
        return
    
    if sys.platform == 'win32':
        try:
            loop = asyncio.get_event_loop()
            loop_type = type(loop).__name__
            
            # Use thread pool workaround if ProactorEventLoop is detected
            if 'Proactor' in loop_type:
                _PLAYWRIGHT_EXECUTOR = ThreadPoolExecutor(
                    max_workers=3,
                    thread_name_prefix="playwright_"
                )
                _WINDOWS_WORKAROUND_ENABLED = True
                logger.info(
                    "Windows ProactorEventLoop detected - Using thread pool workaround "
                    "for Playwright compatibility"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize Playwright executor: {e}")


def _sync_crawl_with_playwright(url: str, config: CrawlConfig) -> CrawlResult:
    """
    Synchronous crawl function that runs in a separate thread.
    Creates its own event loop with WindowsSelectorEventLoop.
    """
    import asyncio
    
    # Create new event loop for this thread with WindowsSelectorEventLoop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.debug("Set WindowsSelectorEventLoopPolicy for this thread")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop_type = type(loop).__name__
    logger.info(f"Thread pool crawl using event loop: {loop_type}")
    
    try:
        # Run the actual crawl in this thread's event loop
        result = loop.run_until_complete(_do_playwright_crawl(url, config))
        return result
    finally:
        loop.close()


async def _do_playwright_crawl(url: str, config: CrawlConfig) -> CrawlResult:
    """
    Actual Playwright crawl implementation.
    This runs in its own event loop (WindowsSelectorEventLoop on Windows).
    """
    start_time = time.time()
    
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        
        # Configure browser
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
        )
        
        # Configure crawler run
        crawler_config = CrawlerRunConfig(
            wait_until="networkidle",
            page_timeout=int(config.timeout * 1000),  # Convert to ms
            remove_overlay_elements=True,
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=crawler_config,
            )
            
            crawl_time = time.time() - start_time
            
            if result.success:
                # Extract content based on mode
                if config.extract_mode == ExtractMode.MARKDOWN:
                    content = result.markdown or ""
                elif config.extract_mode == ExtractMode.TEXT:
                    content = result.extracted_content or result.markdown or ""
                else:
                    content = result.html or ""
                
                # Truncate if too long (max 500KB)
                max_length = 500000
                if len(content) > max_length:
                    content = content[:max_length]
                    logger.debug(f"Truncated content for {url}")
                
                # Get title
                title = ""
                if result.metadata:
                    title = result.metadata.get("title", "")
                
                logger.info(
                    f"Crawled {url}: {len(content)} chars in {crawl_time:.2f}s"
                )
                
                return CrawlResult(
                    url=url,
                    status=CrawlStatus.SUCCESS,
                    title=title,
                    content=content,
                    status_code=200,
                    crawl_time=crawl_time,
                    crawled_at=datetime.utcnow(),
                )
            else:
                error_msg = result.error_message or "Unknown error"
                logger.warning(f"Crawl failed for {url}: {error_msg}")
                
                return CrawlResult(
                    url=url,
                    status=CrawlStatus.ERROR,
                    error_message=error_msg,
                    crawl_time=crawl_time,
                    crawled_at=datetime.utcnow(),
                )
                
    except asyncio.TimeoutError:
        crawl_time = time.time() - start_time
        logger.warning(f"Crawl timeout for {url}")
        return CrawlResult(
            url=url,
            status=CrawlStatus.TIMEOUT,
            error_message=f"Timeout after {config.timeout}s",
            crawl_time=crawl_time,
            crawled_at=datetime.utcnow(),
        )
    except ImportError:
        logger.error("crawl4ai not installed")
        raise CrawlError(
            "crawl4ai is not installed. Run: pip install crawl4ai",
            code="CRAWL_DEPENDENCY_ERROR",
        )
    except Exception as e:
        crawl_time = time.time() - start_time
        logger.error(f"Crawl error for {url}: {e}")
        return CrawlResult(
            url=url,
            status=CrawlStatus.ERROR,
            error_message=str(e),
            crawl_time=crawl_time,
            crawled_at=datetime.utcnow(),
        )


class Crawl4AIService(CrawlService):
    """
    crawl4ai-based web crawling service.
    
    Uses headless browser to render JavaScript and extract content.
    """
    
    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        default_timeout: Optional[float] = None,
        max_content_length: Optional[int] = None,
        rate_limit: Optional[float] = None,
    ):
        settings = get_settings()
        self.max_concurrent = max_concurrent or settings.crawl.max_concurrent
        self.default_timeout = default_timeout or settings.crawl.timeout
        self.max_content_length = max_content_length or settings.crawl.max_content_length
        self.rate_limit = rate_limit or settings.crawl.rate_limit_per_domain
        self.user_agent = settings.crawl.user_agent
        
        # Track last request time per domain for rate limiting
        self._domain_last_request: dict[str, float] = {}
        self._rate_limit_lock = asyncio.Lock()
    
    async def _wait_for_rate_limit(self, domain: str) -> None:
        """Wait if needed to respect rate limit for domain."""
        async with self._rate_limit_lock:
            now = time.time()
            last_request = self._domain_last_request.get(domain, 0)
            elapsed = now - last_request
            
            if elapsed < self.rate_limit:
                wait_time = self.rate_limit - elapsed
                logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            
            self._domain_last_request[domain] = time.time()
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    async def crawl(
        self,
        url: str,
        config: Optional[CrawlConfig] = None,
    ) -> CrawlResult:
        """
        Crawl a single URL using crawl4ai.
        
        On Windows with ProactorEventLoop, uses thread pool workaround
        to run Playwright in WindowsSelectorEventLoop.
        """
        config = config or CrawlConfig(timeout=self.default_timeout)
        domain = self._get_domain(url)
        
        # SSRF protection: block private/internal IPs
        ssrf_error = validate_url_for_ssrf(url)
        if ssrf_error:
            logger.warning(f"SSRF protection blocked URL: {url} — {ssrf_error}")
            return CrawlResult(
                url=url,
                status=CrawlStatus.ERROR,
                error_message=f"URL blocked: {ssrf_error}",
                crawled_at=datetime.utcnow(),
            )
        
        # Initialize Windows workaround if needed
        if sys.platform == 'win32':
            _init_playwright_executor()
        
        # Rate limiting
        await self._wait_for_rate_limit(domain)
        
        logger.debug(f"Crawling: {url}")
        
        # On Windows, use simple HTTP crawler as fallback
        if sys.platform == 'win32':
            logger.info(f"Using simple HTTP crawler for Windows: {url}")
            from src.services.crawl.simple_crawler import simple_http_crawl
            return await simple_http_crawl(url, config)
        
        # Linux/Mac: Use Playwright directly
        logger.info(f"Using Playwright crawler for: {url}")
        return await _do_playwright_crawl(url, config)
    
    async def crawl_many(
        self,
        urls: list[str],
        config: Optional[CrawlConfig] = None,
        max_concurrent: Optional[int] = None,
    ) -> CrawlBatchResult:
        """
        Crawl multiple URLs in parallel with concurrency limit.
        """
        # Limit batch size to prevent resource exhaustion (configurable)
        from src.config import get_settings
        max_batch = get_settings().crawl.max_urls_per_request
        if len(urls) > max_batch:
            logger.warning(
                f"Batch crawl request with {len(urls)} URLs exceeds limit of {max_batch}. "
                "Truncating to max batch size."
            )
            urls = urls[:max_batch]
        
        max_concurrent = max_concurrent or self.max_concurrent
        config = config or CrawlConfig(timeout=self.default_timeout)
        
        logger.info(f"Starting batch crawl of {len(urls)} URLs (max concurrent: {max_concurrent})")
        start_time = time.time()
        
        # Use semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def crawl_with_semaphore(url: str) -> CrawlResult:
            async with semaphore:
                return await self.crawl(url, config)
        
        # Execute all crawls
        tasks = [crawl_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        crawl_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Crawl task failed for {urls[i]}: {result}")
                crawl_results.append(CrawlResult(
                    url=urls[i],
                    status=CrawlStatus.ERROR,
                    error_message=str(result),
                    crawled_at=datetime.utcnow(),
                ))
            else:
                crawl_results.append(result)
        
        total_time = time.time() - start_time
        batch_result = CrawlBatchResult(
            results=crawl_results,
            total_time=total_time,
        )
        
        logger.info(
            f"Batch crawl complete: {len(batch_result.successful)}/{len(urls)} "
            f"successful in {total_time:.2f}s"
        )
        
        return batch_result
    
    async def health_check(self) -> bool:
        """Check if crawl4ai is available."""
        try:
            from crawl4ai import AsyncWebCrawler
            # Just check import works
            return True
        except ImportError:
            return False
