"""
Simple HTTP-based crawler for Windows fallback.

Used when Playwright is not available (Windows development).
"""

import httpx
import time
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

from src.services.crawl.models import (
    CrawlConfig,
    CrawlResult,
    CrawlStatus,
    ExtractMode,
)
from src.utils.logging import get_logger
from src.utils.url_validation import validate_url_for_ssrf

logger = get_logger(__name__)


async def simple_http_crawl(url: str, config: CrawlConfig) -> CrawlResult:
    """
    Simple HTTP-based crawler using httpx and BeautifulSoup.
    
    Fallback for Windows where Playwright doesn't work.
    """
    start_time = time.time()
    
    # SSRF protection: block private/internal IPs
    ssrf_error = validate_url_for_ssrf(url)
    if ssrf_error:
        logger.warning(f"SSRF protection blocked URL: {url} — {ssrf_error}")
        return CrawlResult(
            url=url,
            status=CrawlStatus.ERROR,
            error_message=f"URL blocked: {ssrf_error}",
            crawl_time=0.0,
            crawled_at=datetime.utcnow(),
        )
    
    try:
        async with httpx.AsyncClient(
            timeout=config.timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        ) as client:
            response = await client.get(url)
            
            crawl_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return CrawlResult(
                    url=url,
                    status=CrawlStatus.ERROR,
                    error_message=f"HTTP {response.status_code}",
                    status_code=response.status_code,
                    crawl_time=crawl_time,
                    crawled_at=datetime.utcnow(),
                )
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text() if title_tag else ""
            
            # Extract content based on mode
            if config.extract_mode == ExtractMode.HTML:
                content = str(soup)
            elif config.extract_mode == ExtractMode.TEXT:
                content = soup.get_text(separator='\n', strip=True)
            else:  # MARKDOWN (simplified)
                # Get main content areas
                main_content = soup.find('main') or soup.find('article') or soup.find('body')
                if main_content:
                    content = main_content.get_text(separator='\n', strip=True)
                else:
                    content = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            content = '\n'.join(lines)
            
            # Truncate if too long
            max_length = 500000
            if len(content) > max_length:
                content = content[:max_length]
                logger.debug(f"Truncated content for {url}")
            
            logger.info(
                f"[HTTP] Crawled {url}: {len(content)} chars in {crawl_time:.2f}s"
            )
            
            return CrawlResult(
                url=url,
                status=CrawlStatus.SUCCESS,
                title=title.strip(),
                content=content,
                status_code=response.status_code,
                crawl_time=crawl_time,
                crawled_at=datetime.utcnow(),
            )
            
    except httpx.TimeoutException:
        crawl_time = time.time() - start_time
        logger.warning(f"HTTP timeout for {url}")
        return CrawlResult(
            url=url,
            status=CrawlStatus.TIMEOUT,
            error_message=f"Timeout after {config.timeout}s",
            crawl_time=crawl_time,
            crawled_at=datetime.utcnow(),
        )
    except Exception as e:
        crawl_time = time.time() - start_time
        logger.error(f"HTTP crawl error for {url}: {e}")
        return CrawlResult(
            url=url,
            status=CrawlStatus.ERROR,
            error_message=str(e),
            crawl_time=crawl_time,
            crawled_at=datetime.utcnow(),
        )
