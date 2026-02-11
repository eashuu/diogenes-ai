"""
Source quality scoring.

Evaluates the quality and relevance of sources and content.
"""

from typing import Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse

from src.processing.models import ContentChunk
from src.services.crawl.models import CrawlResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Academic/research domains for badge detection
ACADEMIC_DOMAINS = {
    "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org",
    "nih.gov", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com",
    "researchgate.net", "sciencedirect.com", "springer.com",
    "jstor.org", "wiley.com", "sagepub.com", "tandfonline.com"
}

# Primary source domains (original data/research)
PRIMARY_SOURCE_DOMAINS = {
    "arxiv.org", "nih.gov", "cdc.gov", "who.int", "census.gov",
    "bls.gov", "sec.gov", "data.gov", "europa.eu", "un.org"
}


class QualityScorer:
    """
    Multi-factor quality scoring for sources and content.
    
    Factors considered:
    - Domain authority
    - Content freshness
    - Content density/quality
    - Relevance to query
    """
    
    # Domain authority scores (0.0 - 1.0)
    DOMAIN_SCORES = {
        # High authority
        "edu": 0.9,
        "gov": 0.9,
        "org": 0.75,
        
        # Known high-quality domains
        "arxiv.org": 0.95,
        "nature.com": 0.95,
        "science.org": 0.95,
        "ieee.org": 0.9,
        "acm.org": 0.9,
        "nih.gov": 0.9,
        "cdc.gov": 0.9,
        "who.int": 0.9,
        
        # Tech/Development
        "github.com": 0.85,
        "stackoverflow.com": 0.8,
        "docs.python.org": 0.85,
        "developer.mozilla.org": 0.85,
        "kubernetes.io": 0.85,
        
        # News/Media
        "reuters.com": 0.8,
        "apnews.com": 0.8,
        "bbc.com": 0.75,
        "nytimes.com": 0.75,
        "theguardian.com": 0.75,
        "washingtonpost.com": 0.75,
        
        # Reference
        "wikipedia.org": 0.7,
        "britannica.com": 0.8,
        
        # Tech News
        "techcrunch.com": 0.7,
        "wired.com": 0.7,
        "arstechnica.com": 0.75,
        
        # Default
        "com": 0.5,
        "net": 0.5,
        "io": 0.6,
    }
    
    # Low quality indicators
    LOW_QUALITY_PATTERNS = [
        "clickbait",
        "sponsored",
        "advertisement",
        "affiliate",
        "buy now",
        "limited time",
        "act now",
        "click here",
    ]
    
    def __init__(
        self,
        authority_weight: float = 0.3,
        freshness_weight: float = 0.2,
        relevance_weight: float = 0.3,
        quality_weight: float = 0.2,
    ):
        self.authority_weight = authority_weight
        self.freshness_weight = freshness_weight
        self.relevance_weight = relevance_weight
        self.quality_weight = quality_weight
    
    def score_domain(self, url: str) -> float:
        """
        Score domain authority.
        
        Args:
            url: Source URL
            
        Returns:
            Authority score (0.0 - 1.0)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]
            
            # Check exact domain match
            if domain in self.DOMAIN_SCORES:
                return self.DOMAIN_SCORES[domain]
            
            # Check parent domain (e.g., docs.example.com -> example.com)
            parts = domain.split(".")
            if len(parts) >= 2:
                parent = ".".join(parts[-2:])
                if parent in self.DOMAIN_SCORES:
                    return self.DOMAIN_SCORES[parent]
            
            # Check TLD
            tld = parts[-1] if parts else ""
            if tld in self.DOMAIN_SCORES:
                return self.DOMAIN_SCORES[tld]
            
            # Default score
            return 0.5
            
        except Exception as e:
            logger.warning(f"Error scoring domain {url}: {e}")
            return 0.5
    
    def score_freshness(
        self,
        crawled_at: Optional[datetime] = None,
        published_at: Optional[datetime] = None,
        max_age_days: int = 365,
    ) -> float:
        """
        Score content freshness.
        
        Args:
            crawled_at: When content was crawled
            published_at: When content was published (if known)
            max_age_days: Maximum age before score drops to 0
            
        Returns:
            Freshness score (0.0 - 1.0)
        """
        # Use published date if available, otherwise crawled date
        reference_date = published_at or crawled_at or datetime.utcnow()
        
        age = datetime.utcnow() - reference_date
        age_days = age.days
        
        if age_days <= 0:
            return 1.0
        elif age_days >= max_age_days:
            return 0.1  # Minimum freshness score
        else:
            # Linear decay
            return 1.0 - (age_days / max_age_days) * 0.9
    
    def score_content_quality(self, content: str) -> float:
        """
        Score content quality based on text characteristics.
        
        Args:
            content: Text content
            
        Returns:
            Quality score (0.0 - 1.0)
        """
        if not content:
            return 0.0
        
        score = 0.5  # Base score
        
        content_lower = content.lower()
        
        # Negative factors
        for pattern in self.LOW_QUALITY_PATTERNS:
            if pattern in content_lower:
                score -= 0.1
        
        # Word count factor (prefer longer, detailed content)
        word_count = len(content.split())
        if word_count > 500:
            score += 0.2
        elif word_count > 200:
            score += 0.1
        elif word_count < 50:
            score -= 0.2
        
        # Sentence structure (periods indicate proper sentences)
        sentence_count = content.count('. ') + content.count('.\n')
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        if 10 <= avg_sentence_length <= 30:
            score += 0.1  # Good sentence length
        
        # Code presence (often indicates technical content)
        if '```' in content or '    ' in content:
            score += 0.05
        
        # References/citations
        if '[' in content and ']' in content:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def score_relevance(
        self,
        content: str,
        query: str,
        query_terms: Optional[list[str]] = None,
    ) -> float:
        """
        Score content relevance to query.
        
        Simple keyword-based relevance (can be enhanced with embeddings).
        
        Args:
            content: Text content
            query: User query
            query_terms: Pre-extracted query terms
            
        Returns:
            Relevance score (0.0 - 1.0)
        """
        if not content or not query:
            return 0.0
        
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Extract terms from query if not provided
        if query_terms is None:
            # Simple tokenization
            query_terms = [
                term for term in query_lower.split()
                if len(term) > 2 and term.isalnum()
            ]
        
        if not query_terms:
            return 0.5
        
        # Count term matches
        matches = sum(1 for term in query_terms if term in content_lower)
        match_ratio = matches / len(query_terms)
        
        # Exact query match bonus
        if query_lower in content_lower:
            match_ratio = min(1.0, match_ratio + 0.3)
        
        return match_ratio
    
    def score_source(
        self,
        crawl_result: CrawlResult,
        query: Optional[str] = None,
    ) -> float:
        """
        Calculate overall quality score for a source.
        
        Args:
            crawl_result: Crawled page data
            query: Optional query for relevance scoring
            
        Returns:
            Overall score (0.0 - 1.0)
        """
        # Calculate individual scores
        authority = self.score_domain(crawl_result.url)
        freshness = self.score_freshness(crawl_result.crawled_at)
        quality = self.score_content_quality(crawl_result.content)
        
        relevance = 0.5  # Default if no query
        if query:
            relevance = self.score_relevance(crawl_result.content, query)
        
        # Weighted average
        overall = (
            authority * self.authority_weight +
            freshness * self.freshness_weight +
            quality * self.quality_weight +
            relevance * self.relevance_weight
        )
        
        logger.debug(
            f"Score for {crawl_result.url}: "
            f"auth={authority:.2f}, fresh={freshness:.2f}, "
            f"qual={quality:.2f}, rel={relevance:.2f}, "
            f"overall={overall:.6f}"
        )
        # Defensive clamp: ensure overall is within expected 0.0-1.0 range
        if overall < 0.0 or overall > 1.0:
            logger.warning(
                f"Computed overall score out of range for {crawl_result.url}: {overall:.6f}. Clamping to [0,1]."
            )
        overall = max(0.0, min(1.0, overall))

        return overall
    
    def score_chunk(
        self,
        chunk: ContentChunk,
        query: Optional[str] = None,
    ) -> float:
        """
        Calculate quality score for a content chunk.
        """
        authority = self.score_domain(chunk.source_url)
        quality = self.score_content_quality(chunk.content)
        
        relevance = 0.5
        if query:
            relevance = self.score_relevance(chunk.content, query)
        
        # Chunks don't have freshness info, so redistribute weight
        adjusted_auth_weight = self.authority_weight + self.freshness_weight / 2
        adjusted_qual_weight = self.quality_weight + self.freshness_weight / 2
        
        value = (
            authority * adjusted_auth_weight +
            quality * adjusted_qual_weight +
            relevance * self.relevance_weight
        )

        # Defensive clamp for chunk scores as well
        if value < 0.0 or value > 1.0:
            logger.warning(
                f"Computed chunk score out of range for {chunk.source_url}: {value:.6f}. Clamping to [0,1]."
            )
        return max(0.0, min(1.0, value))
        
    
    def rank_sources(
        self,
        crawl_results: list[CrawlResult],
        query: Optional[str] = None,
    ) -> list[tuple[CrawlResult, float]]:
        """
        Rank sources by quality score.
        
        Returns:
            List of (result, score) tuples, sorted by score descending
        """
        scored = [
            (result, self.score_source(result, query))
            for result in crawl_results
            if result.is_success
        ]
        
        return sorted(scored, key=lambda x: x[1], reverse=True)
    
    def rank_chunks(
        self,
        chunks: list[ContentChunk],
        query: Optional[str] = None,
    ) -> list[tuple[ContentChunk, float]]:
        """
        Rank chunks by quality score.
        """
        scored = [
            (chunk, self.score_chunk(chunk, query))
            for chunk in chunks
        ]
        
        return sorted(scored, key=lambda x: x[1], reverse=True)
    
    def compute_badges(
        self,
        url: str,
        authority_score: float,
        freshness_score: float,
        verified: bool = False
    ) -> dict[str, bool]:
        """
        Compute quality badges for a source.
        
        Args:
            url: Source URL
            authority_score: Domain authority score (0-1)
            freshness_score: Content freshness score (0-1)
            verified: Whether source was cross-referenced
            
        Returns:
            Dictionary of badge flags
        """
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            domain = ""
        
        # Check if academic domain
        is_academic = any(
            domain == ad or domain.endswith("." + ad)
            for ad in ACADEMIC_DOMAINS
        )
        
        # Check if primary source
        is_primary = any(
            domain == pd or domain.endswith("." + pd)
            for pd in PRIMARY_SOURCE_DOMAINS
        )
        
        # Also check TLD for academic indicators
        if domain.endswith(".edu") or domain.endswith(".ac.uk"):
            is_academic = True
        
        return {
            "is_verified": verified,
            "is_recent": freshness_score >= 0.7,
            "is_authoritative": authority_score >= 0.8,
            "is_primary_source": is_primary,
            "is_academic": is_academic
        }
    
    def get_score_breakdown(
        self,
        crawl_result: CrawlResult,
        query: Optional[str] = None
    ) -> dict[str, float]:
        """
        Get detailed score breakdown for a source.
        
        Args:
            crawl_result: Crawled page data
            query: Optional query for relevance
            
        Returns:
            Dictionary with individual score components
        """
        authority = self.score_domain(crawl_result.url)
        freshness = self.score_freshness(crawl_result.crawled_at)
        quality = self.score_content_quality(crawl_result.content)
        relevance = self.score_relevance(crawl_result.content, query) if query else 0.5
        
        return {
            "authority": round(authority, 3),
            "freshness": round(freshness, 3),
            "relevance": round(relevance, 3),
            "content_quality": round(quality, 3)
        }
