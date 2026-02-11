"""
Crawl service models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal
from enum import Enum
import hashlib


class ExtractMode(str, Enum):
    """Content extraction mode."""
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"


class CrawlStatus(str, Enum):
    """Status of a crawl operation."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class CrawlRequestConfig:
    """Configuration for a single crawl request.
    
    Note: This is different from src.config.CrawlConfig which is for
    application-level crawler settings.
    """
    
    timeout: float = 30.0
    extract_mode: ExtractMode = ExtractMode.MARKDOWN
    wait_for_selector: Optional[str] = None
    wait_time: float = 0.0
    remove_selectors: list[str] = field(default_factory=lambda: [
        "nav", "header", "footer", "aside", ".sidebar", ".advertisement",
        ".ads", ".cookie-banner", ".popup", "#comments"
    ])
    max_content_length: int = 500000
    screenshot: bool = False


# Alias for backward compatibility
CrawlConfig = CrawlRequestConfig
    

@dataclass
class CrawlResult:
    """Result of crawling a single URL."""
    
    url: str
    status: CrawlStatus
    title: str = ""
    content: str = ""  # Extracted content (markdown/text/html)
    raw_html: Optional[str] = None
    
    # Metadata
    status_code: int = 0
    content_type: str = ""
    content_length: int = 0
    crawl_time: float = 0.0
    crawled_at: datetime = field(default_factory=datetime.utcnow)
    
    # Error info (if status != SUCCESS)
    error_message: Optional[str] = None
    
    # Computed fields
    content_hash: str = ""
    word_count: int = 0
    
    def __post_init__(self):
        """Compute derived fields."""
        if self.content and not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
        if self.content and not self.word_count:
            self.word_count = len(self.content.split())
        if self.content and not self.content_length:
            self.content_length = len(self.content)
    
    @property
    def is_success(self) -> bool:
        return self.status == CrawlStatus.SUCCESS
    
    @property
    def has_content(self) -> bool:
        return bool(self.content and self.content.strip())
    
    def truncate_content(self, max_length: int) -> str:
        """Get truncated content."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        return urlparse(self.url).netloc
    
    @property
    def favicon_url(self) -> str:
        """Get favicon URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"


@dataclass
class CrawlBatchResult:
    """Result of crawling multiple URLs."""
    
    results: list[CrawlResult]
    total_time: float = 0.0
    
    @property
    def successful(self) -> list[CrawlResult]:
        """Get successful crawl results."""
        return [r for r in self.results if r.is_success]
    
    @property
    def failed(self) -> list[CrawlResult]:
        """Get failed crawl results."""
        return [r for r in self.results if not r.is_success]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if not self.results:
            return 0.0
        return len(self.successful) / len(self.results)
    
    def get_contents(self) -> list[tuple[str, str, str]]:
        """Get (url, title, content) tuples for successful crawls."""
        return [
            (r.url, r.title, r.content)
            for r in self.successful
            if r.has_content
        ]
