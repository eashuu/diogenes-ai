"""
ArXiv API Integration.

Provides search and paper retrieval from arXiv.org.
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field
from urllib.parse import urlencode
from xml.etree.ElementTree import Element
import defusedxml.ElementTree as ET

import httpx

from src.utils.logging import get_logger
from src.utils.retry import with_retry


logger = get_logger(__name__)


# ArXiv API base URL
ARXIV_API_URL = "http://export.arxiv.org/api/query"


@dataclass
class ArxivAuthor:
    """Author information from arXiv."""
    name: str
    affiliation: Optional[str] = None


@dataclass
class ArxivPaper:
    """Paper information from arXiv."""
    arxiv_id: str
    title: str
    summary: str
    authors: list[ArxivAuthor]
    categories: list[str]
    primary_category: str
    published: datetime
    updated: datetime
    pdf_url: str
    abs_url: str
    doi: Optional[str] = None
    journal_ref: Optional[str] = None
    comment: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "summary": self.summary,
            "authors": [{"name": a.name, "affiliation": a.affiliation} for a in self.authors],
            "categories": self.categories,
            "primary_category": self.primary_category,
            "published": self.published.isoformat(),
            "updated": self.updated.isoformat(),
            "pdf_url": self.pdf_url,
            "abs_url": self.abs_url,
            "doi": self.doi,
            "journal_ref": self.journal_ref,
            "comment": self.comment
        }


@dataclass 
class ArxivSearchResult:
    """Search result from arXiv API."""
    papers: list[ArxivPaper]
    total_results: int
    start_index: int
    items_per_page: int
    query: str


class ArxivService:
    """
    ArXiv API client for searching and retrieving papers.
    
    Features:
    - Full-text search
    - Category filtering
    - Date range filtering
    - Author search
    - Paper retrieval by ID
    - PDF URL generation
    
    Usage:
        service = ArxivService()
        
        # Search for papers
        result = await service.search("transformer attention mechanism", max_results=10)
        for paper in result.papers:
            print(paper.title, paper.arxiv_id)
        
        # Get specific paper
        paper = await service.get_paper("2103.14030")
    
    Note: ArXiv has rate limits. This service includes delays between requests.
    """
    
    def __init__(
        self,
        timeout: float = 30.0,
        rate_limit_delay: float = 3.0  # ArXiv recommends 3 second delay
    ):
        """
        Initialize ArXiv service.
        
        Args:
            timeout: Request timeout in seconds
            rate_limit_delay: Delay between requests (ArXiv recommends 3s)
        """
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Diogenes/2.0 (research assistant)"
                }
            )
        return self._client
    
    async def _rate_limit(self):
        """Apply rate limiting."""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = datetime.now()
    
    @with_retry(max_attempts=3, base_delay=2.0)
    async def search(
        self,
        query: str,
        max_results: int = 10,
        start: int = 0,
        sort_by: str = "relevance",  # "relevance", "lastUpdatedDate", "submittedDate"
        sort_order: str = "descending",  # "ascending", "descending"
        categories: Optional[list[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> ArxivSearchResult:
        """
        Search arXiv for papers.
        
        Args:
            query: Search query (supports AND, OR, ANDNOT, field prefixes)
            max_results: Maximum papers to return (max 100 per request)
            start: Starting index for pagination
            sort_by: Sort field
            sort_order: Sort direction
            categories: Filter by arXiv categories (e.g., "cs.AI", "cs.LG")
            date_from: Filter papers published after this date
            date_to: Filter papers published before this date
            
        Returns:
            ArxivSearchResult with matching papers
        
        Query syntax examples:
            - "quantum computing" - Simple search
            - "ti:attention mechanism" - Title search
            - "au:bengio" - Author search
            - "abs:transformer" - Abstract search
            - "cat:cs.AI" - Category search
            - "quantum AND computing" - Boolean AND
            - "quantum OR classical" - Boolean OR
        """
        await self._rate_limit()
        
        # Build search query
        search_query = self._build_query(query, categories, date_from, date_to)
        
        # Map sort options
        sort_by_map = {
            "relevance": "relevance",
            "lastUpdatedDate": "lastUpdatedDate",
            "submittedDate": "submittedDate"
        }
        
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": min(max_results, 100),  # ArXiv limit
            "sortBy": sort_by_map.get(sort_by, "relevance"),
            "sortOrder": sort_order
        }
        
        url = f"{ARXIV_API_URL}?{urlencode(params)}"
        
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        
        # Parse XML response
        papers, total = self._parse_response(response.text)
        
        logger.info(f"ArXiv search '{query}': found {total} results, returned {len(papers)}")
        
        return ArxivSearchResult(
            papers=papers,
            total_results=total,
            start_index=start,
            items_per_page=min(max_results, 100),
            query=query
        )
    
    def _build_query(
        self,
        query: str,
        categories: Optional[list[str]],
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> str:
        """Build arXiv query string."""
        parts = []
        
        # Main query (search all fields if no prefix)
        if query:
            # If no field prefix, search in all
            if not any(query.startswith(p) for p in ["ti:", "au:", "abs:", "cat:", "all:"]):
                query = f"all:{query}"
            parts.append(query)
        
        # Category filter
        if categories:
            cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
            parts.append(f"({cat_query})")
        
        # Date filter (using submittedDate)
        # Note: arXiv date filtering is limited, this is a basic implementation
        # Format: YYYYMMDDHHMMSS
        if date_from:
            # ArXiv doesn't support date range in query directly
            # This would need post-filtering
            pass
        
        return " AND ".join(parts) if parts else "all:*"
    
    def _parse_response(self, xml_text: str) -> tuple[list[ArxivPaper], int]:
        """Parse arXiv API XML response."""
        # XML namespaces
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/"
        }
        
        root = ET.fromstring(xml_text)
        
        # Get total results
        total_elem = root.find("opensearch:totalResults", ns)
        total = int(total_elem.text) if total_elem is not None and total_elem.text else 0
        
        papers = []
        
        for entry in root.findall("atom:entry", ns):
            try:
                paper = self._parse_entry(entry, ns)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.debug(f"Failed to parse entry: {e}")
                continue
        
        return papers, total
    
    def _parse_entry(self, entry: Element, ns: dict) -> Optional[ArxivPaper]:
        """Parse a single entry element."""
        # Get ID
        id_elem = entry.find("atom:id", ns)
        if id_elem is None or not id_elem.text:
            return None
        
        arxiv_id = id_elem.text.split("/abs/")[-1]
        
        # Get title
        title_elem = entry.find("atom:title", ns)
        title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else ""
        
        # Get summary
        summary_elem = entry.find("atom:summary", ns)
        summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
        
        # Get authors
        authors = []
        for author_elem in entry.findall("atom:author", ns):
            name_elem = author_elem.find("atom:name", ns)
            affil_elem = author_elem.find("arxiv:affiliation", ns)
            if name_elem is not None and name_elem.text:
                authors.append(ArxivAuthor(
                    name=name_elem.text,
                    affiliation=affil_elem.text if affil_elem is not None else None
                ))
        
        # Get categories
        categories = []
        primary_category = ""
        
        primary_elem = entry.find("arxiv:primary_category", ns)
        if primary_elem is not None:
            primary_category = primary_elem.get("term", "")
        
        for cat_elem in entry.findall("atom:category", ns):
            term = cat_elem.get("term")
            if term:
                categories.append(term)
        
        # Get dates
        published_elem = entry.find("atom:published", ns)
        updated_elem = entry.find("atom:updated", ns)
        
        published = self._parse_date(published_elem.text) if published_elem is not None and published_elem.text else datetime.now()
        updated = self._parse_date(updated_elem.text) if updated_elem is not None and updated_elem.text else published
        
        # Get links
        pdf_url = ""
        abs_url = ""
        for link_elem in entry.findall("atom:link", ns):
            link_type = link_elem.get("type", "")
            link_href = link_elem.get("href", "")
            link_title = link_elem.get("title", "")
            
            if link_title == "pdf" or link_type == "application/pdf":
                pdf_url = link_href
            elif link_type == "text/html":
                abs_url = link_href
        
        # Fallback URLs
        if not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        if not abs_url:
            abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        
        # Get optional fields
        doi_elem = entry.find("arxiv:doi", ns)
        doi = doi_elem.text if doi_elem is not None and doi_elem.text else None
        
        journal_elem = entry.find("arxiv:journal_ref", ns)
        journal_ref = journal_elem.text if journal_elem is not None and journal_elem.text else None
        
        comment_elem = entry.find("arxiv:comment", ns)
        comment = comment_elem.text if comment_elem is not None and comment_elem.text else None
        
        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            pdf_url=pdf_url,
            abs_url=abs_url,
            doi=doi,
            journal_ref=journal_ref,
            comment=comment
        )
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse ISO date string."""
        try:
            # Handle various formats
            date_str = date_str.replace("Z", "+00:00")
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("+00:00", ""))
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception:
            return datetime.now()
    
    async def get_paper(self, arxiv_id: str) -> Optional[ArxivPaper]:
        """
        Get a specific paper by arXiv ID.
        
        Args:
            arxiv_id: ArXiv ID (e.g., "2103.14030" or "cs.AI/0101001")
            
        Returns:
            ArxivPaper if found, None otherwise
        """
        await self._rate_limit()
        
        # Clean ID
        arxiv_id = arxiv_id.strip()
        if arxiv_id.startswith("arXiv:"):
            arxiv_id = arxiv_id[6:]
        
        params = {
            "id_list": arxiv_id,
            "max_results": 1
        }
        
        url = f"{ARXIV_API_URL}?{urlencode(params)}"
        
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        
        papers, _ = self._parse_response(response.text)
        
        if papers:
            logger.debug(f"Retrieved paper: {papers[0].title}")
            return papers[0]
        
        return None
    
    async def get_papers(self, arxiv_ids: list[str]) -> list[ArxivPaper]:
        """
        Get multiple papers by arXiv IDs.
        
        Args:
            arxiv_ids: List of arXiv IDs
            
        Returns:
            List of found papers
        """
        await self._rate_limit()
        
        # Clean IDs
        clean_ids = []
        for aid in arxiv_ids:
            aid = aid.strip()
            if aid.startswith("arXiv:"):
                aid = aid[6:]
            clean_ids.append(aid)
        
        params = {
            "id_list": ",".join(clean_ids),
            "max_results": len(clean_ids)
        }
        
        url = f"{ARXIV_API_URL}?{urlencode(params)}"
        
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        
        papers, _ = self._parse_response(response.text)
        
        logger.debug(f"Retrieved {len(papers)} papers by ID")
        return papers
    
    async def search_by_author(
        self,
        author_name: str,
        max_results: int = 20
    ) -> ArxivSearchResult:
        """
        Search papers by author name.
        
        Args:
            author_name: Author name to search
            max_results: Maximum results
            
        Returns:
            ArxivSearchResult
        """
        query = f"au:{author_name}"
        return await self.search(query, max_results=max_results, sort_by="submittedDate")
    
    async def search_by_category(
        self,
        categories: list[str],
        max_results: int = 20,
        days_back: int = 30
    ) -> ArxivSearchResult:
        """
        Get recent papers from specific categories.
        
        Args:
            categories: ArXiv categories (e.g., ["cs.AI", "cs.LG"])
            max_results: Maximum results
            days_back: Look back this many days
            
        Returns:
            ArxivSearchResult
        """
        query = " OR ".join(f"cat:{cat}" for cat in categories)
        return await self.search(
            query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending"
        )
    
    async def get_similar_papers(
        self,
        arxiv_id: str,
        max_results: int = 10
    ) -> list[ArxivPaper]:
        """
        Find papers similar to a given paper.
        
        Uses the paper's categories and title keywords to find related work.
        
        Args:
            arxiv_id: Reference paper ID
            max_results: Maximum results
            
        Returns:
            List of similar papers
        """
        # Get the reference paper
        ref_paper = await self.get_paper(arxiv_id)
        if not ref_paper:
            return []
        
        # Extract keywords from title
        stop_words = {"a", "an", "the", "of", "and", "or", "in", "on", "for", "to", "with", "by"}
        title_words = ref_paper.title.lower().split()
        keywords = [w for w in title_words if len(w) > 3 and w not in stop_words][:5]
        
        # Build query
        keyword_query = " OR ".join(keywords) if keywords else ref_paper.title[:50]
        category_query = f"cat:{ref_paper.primary_category}" if ref_paper.primary_category else ""
        
        query = f"({keyword_query})"
        if category_query:
            query = f"{query} AND {category_query}"
        
        result = await self.search(query, max_results=max_results + 1)
        
        # Filter out the reference paper
        similar = [p for p in result.papers if p.arxiv_id != arxiv_id]
        
        return similar[:max_results]
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Common arXiv categories for AI/ML research
ARXIV_AI_CATEGORIES = [
    "cs.AI",    # Artificial Intelligence
    "cs.LG",    # Machine Learning
    "cs.CL",    # Computation and Language (NLP)
    "cs.CV",    # Computer Vision
    "cs.NE",    # Neural and Evolutionary Computing
    "cs.IR",    # Information Retrieval
    "stat.ML",  # Machine Learning (Statistics)
]

ARXIV_CS_CATEGORIES = [
    "cs.AI", "cs.AR", "cs.CC", "cs.CE", "cs.CG", "cs.CL", "cs.CR", "cs.CV",
    "cs.CY", "cs.DB", "cs.DC", "cs.DL", "cs.DM", "cs.DS", "cs.ET", "cs.FL",
    "cs.GL", "cs.GR", "cs.GT", "cs.HC", "cs.IR", "cs.IT", "cs.LG", "cs.LO",
    "cs.MA", "cs.MM", "cs.MS", "cs.NA", "cs.NE", "cs.NI", "cs.OH", "cs.OS",
    "cs.PF", "cs.PL", "cs.RO", "cs.SC", "cs.SD", "cs.SE", "cs.SI", "cs.SY",
]
