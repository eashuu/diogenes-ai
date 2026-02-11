"""
Content processing models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
import hashlib


@dataclass
class ContentChunk:
    """A chunk of processed content."""
    
    id: str  # Unique chunk ID
    source_url: str
    source_title: str
    content: str
    
    # Position info
    chunk_index: int = 0
    total_chunks: int = 1
    
    # Metrics
    token_count: int = 0
    word_count: int = 0
    char_count: int = 0
    
    # Quality
    quality_score: float = 0.0
    relevance_score: float = 0.0
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.char_count:
            self.char_count = len(self.content)
        if not self.word_count:
            self.word_count = len(self.content.split())
        if not self.token_count:
            # Rough estimate: 1 token ≈ 4 characters
            self.token_count = self.char_count // 4
    
    def _generate_id(self) -> str:
        """Generate unique chunk ID."""
        content_hash = hashlib.sha256(
            f"{self.source_url}:{self.chunk_index}:{self.content[:100]}".encode()
        ).hexdigest()[:12]
        return f"chunk_{content_hash}"
    
    def get_context_header(self) -> str:
        """Get header for use in LLM context."""
        return f"[Source: {self.source_title}]\n[URL: {self.source_url}]\n"


@dataclass
class ExtractedFact:
    """A fact extracted from content with source attribution."""
    
    id: str  # Unique fact ID
    content: str  # The fact statement
    source_chunk_id: str  # Reference to source chunk
    source_url: str
    source_title: str
    
    # Classification
    category: Optional[str] = None  # e.g., "statistic", "claim", "definition"
    confidence: float = 1.0
    
    # For citation
    citation_index: Optional[int] = None
    
    def __post_init__(self):
        if not self.id:
            content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:12]
            self.id = f"fact_{content_hash}"


@dataclass
class ProcessedDocument:
    """A fully processed document."""
    
    url: str
    title: str
    original_content: str
    
    # Processed content
    chunks: list[ContentChunk] = field(default_factory=list)
    facts: list[ExtractedFact] = field(default_factory=list)
    
    # Metrics
    total_tokens: int = 0
    quality_score: float = 0.0
    
    # Metadata
    processed_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
    
    @property
    def fact_count(self) -> int:
        return len(self.facts)
    
    def get_best_chunks(self, n: int = 5) -> list[ContentChunk]:
        """Get top N chunks by quality score."""
        sorted_chunks = sorted(
            self.chunks,
            key=lambda c: c.quality_score,
            reverse=True
        )
        return sorted_chunks[:n]
