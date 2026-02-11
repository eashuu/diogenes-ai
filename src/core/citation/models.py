"""
Citation system models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse


@dataclass
class Source:
    """Represents a source used in research."""
    
    id: str  # Unique source ID
    url: str
    title: str
    
    # Display info
    domain: str = ""
    favicon_url: str = ""
    snippet: str = ""
    
    # Quality metrics
    quality_score: float = 0.0
    
    # Metadata
    crawled_at: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = ""
    word_count: int = 0
    
    # Citation index (assigned during synthesis)
    citation_index: Optional[int] = None
    
    def __post_init__(self):
        if not self.domain and self.url:
            parsed = urlparse(self.url)
            self.domain = parsed.netloc.replace("www.", "")
        
        if not self.favicon_url and self.url:
            parsed = urlparse(self.url)
            self.favicon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
    
    def __hash__(self) -> int:
        return hash(self.url)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Source):
            return False
        return self.url == other.url
    
    def to_source_card(self) -> dict:
        """Convert to source card for frontend display."""
        return {
            "index": self.citation_index,
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "favicon": self.favicon_url,
            "snippet": self.snippet,
            "quality_score": self.quality_score,
        }


@dataclass
class Citation:
    """A specific citation instance in the synthesized answer."""
    
    source_id: str  # Reference to Source
    citation_index: int  # Display index [1], [2], etc.
    
    # Position in answer text
    position: int = 0  # Character position
    
    # What is being cited
    claim: str = ""
    
    # Confidence that this source supports the claim
    confidence: float = 1.0


@dataclass
class CitationMap:
    """
    Tracks all sources and citations for a research session.
    """
    
    sources: dict[str, Source] = field(default_factory=dict)  # id -> Source
    citations: list[Citation] = field(default_factory=list)
    
    # Mapping from source ID to citation index
    _index_map: dict[str, int] = field(default_factory=dict)
    _next_index: int = 1
    
    def add_source(self, source: Source) -> int:
        """
        Add a source and return its citation index.
        
        If source already exists, returns existing index.
        """
        if source.id in self.sources:
            return self._index_map.get(source.id, self._next_index)
        
        # Assign citation index
        citation_index = self._next_index
        self._next_index += 1
        
        source.citation_index = citation_index
        self.sources[source.id] = source
        self._index_map[source.id] = citation_index
        
        return citation_index
    
    def add_citation(
        self,
        source_id: str,
        position: int = 0,
        claim: str = "",
        confidence: float = 1.0,
    ) -> Citation:
        """Add a citation for a source."""
        if source_id not in self.sources:
            raise ValueError(f"Source {source_id} not found")
        
        citation_index = self._index_map[source_id]
        
        citation = Citation(
            source_id=source_id,
            citation_index=citation_index,
            position=position,
            claim=claim,
            confidence=confidence,
        )
        
        self.citations.append(citation)
        return citation
    
    def get_source_by_index(self, index: int) -> Optional[Source]:
        """Get source by citation index."""
        for source in self.sources.values():
            if source.citation_index == index:
                return source
        return None
    
    def get_source_by_url(self, url: str) -> Optional[Source]:
        """Get source by URL."""
        import hashlib
        source_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.sources.get(source_id)
    
    def get_used_sources(self) -> list[Source]:
        """Get sources that have at least one citation."""
        used_ids = {c.source_id for c in self.citations}
        return [
            s for s in self.sources.values()
            if s.id in used_ids
        ]
    
    def get_all_sources(self) -> list[Source]:
        """Get all sources, sorted by citation index."""
        return sorted(
            self.sources.values(),
            key=lambda s: s.citation_index or 999
        )
    
    def get_source_cards(self, used_only: bool = True) -> list[dict]:
        """Get source cards for frontend display."""
        sources = self.get_used_sources() if used_only else self.get_all_sources()
        return [s.to_source_card() for s in sources]
    
    def format_citation_marker(self, source_id: str) -> str:
        """Get formatted citation marker like [1]."""
        if source_id not in self._index_map:
            return ""
        return f"[{self._index_map[source_id]}]"
    
    def clear(self):
        """Clear all sources and citations."""
        self.sources.clear()
        self.citations.clear()
        self._index_map.clear()
        self._next_index = 1
