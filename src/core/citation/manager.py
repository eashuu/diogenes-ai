"""
Citation manager.

Handles citation tracking, source registration, and answer annotation.
"""

from typing import Optional
import re
import hashlib

from src.core.citation.models import Source, Citation, CitationMap
from src.services.crawl.models import CrawlResult
from src.services.search.models import SearchResult
from src.processing.models import ContentChunk
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CitationManager:
    """
    Manages citations throughout the research process.
    
    Responsibilities:
    - Register sources from crawl results
    - Track which sources are used during synthesis
    - Format answers with inline citations [1], [2]
    - Generate source cards for UI
    """
    
    def __init__(self):
        self.citation_map = CitationMap()
        self._chunk_to_source: dict[str, str] = {}  # chunk_id -> source_id
    
    def register_source_from_crawl(
        self,
        crawl_result: CrawlResult,
        quality_score: float = 0.0,
    ) -> Source:
        """
        Register a source from a crawl result.
        
        Returns:
            Registered Source object with assigned citation index
        """
        source_id = self._generate_source_id(crawl_result.url)

        # Sanitize quality_score: coerce to float and clamp to [0.0, 1.0]
        try:
            qs = float(quality_score) if quality_score is not None else 0.0
        except Exception:
            qs = 0.0

        if qs < 0.0 or qs > 1.0:
            logger.warning(
                f"Registering source {crawl_result.url} with out-of-range quality_score={qs}. Clamping to [0,1]."
            )
        qs = max(0.0, min(1.0, qs))

        source = Source(
            id=source_id,
            url=crawl_result.url,
            title=crawl_result.title or crawl_result.domain,
            domain=crawl_result.domain,
            snippet=crawl_result.content[:200] if crawl_result.content else "",
            quality_score=qs,
            crawled_at=crawl_result.crawled_at,
            content_hash=crawl_result.content_hash,
            word_count=crawl_result.word_count,
        )
        
        self.citation_map.add_source(source)
        logger.debug(f"Registered source: [{source.citation_index}] {source.title}")
        
        return source
    
    def register_source_from_search(
        self,
        search_result: SearchResult,
    ) -> Source:
        """Register a source from a search result."""
        source_id = self._generate_source_id(search_result.url)
        # Sanitize incoming score
        try:
            qs = float(search_result.score) if getattr(search_result, "score", None) is not None else 0.0
        except Exception:
            qs = 0.0

        if qs < 0.0 or qs > 1.0:
            logger.warning(
                f"Registering search result {search_result.url} with out-of-range score={qs}. Clamping to [0,1]."
            )
        qs = max(0.0, min(1.0, qs))

        source = Source(
            id=source_id,
            url=search_result.url,
            title=search_result.title,
            domain=search_result.domain,
            snippet=search_result.snippet,
            quality_score=qs,
        )
        
        self.citation_map.add_source(source)
        return source
    
    def register_chunk(self, chunk: ContentChunk, source: Source) -> None:
        """Associate a chunk with its source."""
        self._chunk_to_source[chunk.id] = source.id
    
    def get_source_for_chunk(self, chunk_id: str) -> Optional[Source]:
        """Get the source for a given chunk."""
        source_id = self._chunk_to_source.get(chunk_id)
        if source_id:
            return self.citation_map.sources.get(source_id)
        return None
    
    def _generate_source_id(self, url: str) -> str:
        """Generate a unique ID for a source URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def build_context_with_markers(
        self,
        chunks: list[ContentChunk],
    ) -> str:
        """
        Build context string with source markers for LLM.
        
        Each chunk is prefixed with its source info so the LLM
        knows which source to cite.
        """
        context_parts = []
        
        for chunk in chunks:
            source = self.get_source_for_chunk(chunk.id)
            if source:
                marker = self.citation_map.format_citation_marker(source.id)
                header = f"[Source {marker}: {source.title}]\n"
            else:
                header = f"[Source: {chunk.source_title}]\n"
            
            context_parts.append(header + chunk.content)
        
        return "\n\n---\n\n".join(context_parts)
    
    def annotate_answer(
        self,
        answer: str,
        track_positions: bool = True,
    ) -> str:
        """
        Ensure answer has proper citation formatting.
        
        - Normalizes citation markers to [1], [2], etc.
        - Tracks citation positions
        - Removes citations to non-existent sources
        """
        # Find all citation markers in the answer
        pattern = r'\[(\d+)\]'
        
        def validate_citation(match):
            index = int(match.group(1))
            source = self.citation_map.get_source_by_index(index)
            
            if source:
                if track_positions:
                    self.citation_map.add_citation(
                        source_id=source.id,
                        position=match.start(),
                    )
                return f"[{index}]"
            else:
                # Remove invalid citation
                return ""
        
        annotated = re.sub(pattern, validate_citation, answer)
        
        # Clean up double spaces from removed citations
        annotated = re.sub(r'  +', ' ', annotated)
        
        return annotated
    
    def get_source_cards(self, used_only: bool = True) -> list[dict]:
        """Get source cards for frontend display."""
        return self.citation_map.get_source_cards(used_only)
    
    def get_citation_summary(self) -> dict:
        """Get summary of citations for metadata."""
        return {
            "total_sources": len(self.citation_map.sources),
            "used_sources": len(self.citation_map.get_used_sources()),
            "total_citations": len(self.citation_map.citations),
        }
    
    def reset(self):
        """Reset citation manager for new research."""
        self.citation_map.clear()
        self._chunk_to_source.clear()


class CitationFormatter:
    """
    Formats citations in various output styles.
    """
    
    @staticmethod
    def format_inline(text: str, sources: list[Source]) -> str:
        """
        Format text with inline citation markers.
        
        Replaces [Source N] or similar markers with [1], [2], etc.
        """
        # Map source references to citation indices
        for source in sources:
            if source.citation_index:
                # Replace various source reference formats
                patterns = [
                    rf'\[Source {source.citation_index}\]',
                    rf'\[{source.citation_index}\]',
                    rf'\({source.citation_index}\)',
                ]
                replacement = f"[{source.citation_index}]"
                
                for pattern in patterns:
                    text = re.sub(pattern, replacement, text)
        
        return text
    
    @staticmethod
    def format_footnotes(sources: list[Source]) -> str:
        """
        Format sources as footnotes.
        """
        lines = ["\n\n---\n**Sources:**\n"]
        
        for source in sorted(sources, key=lambda s: s.citation_index or 999):
            if source.citation_index:
                lines.append(f"[{source.citation_index}] [{source.title}]({source.url})")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_bibliography(sources: list[Source]) -> str:
        """
        Format sources in bibliography style.
        """
        lines = ["\n\n## References\n"]
        
        for source in sorted(sources, key=lambda s: s.citation_index or 999):
            if source.citation_index:
                lines.append(
                    f"{source.citation_index}. {source.title}. "
                    f"Retrieved from {source.url}"
                )
        
        return "\n".join(lines)
