"""
Smart content chunking.

Splits content into semantically meaningful chunks while respecting
document structure.
"""

import re
from typing import Optional
import hashlib

from src.config import get_settings
from src.processing.models import ContentChunk
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SmartChunker:
    """
    Semantic-aware content chunker.
    
    Splits content into chunks that:
    - Respect paragraph and section boundaries
    - Maintain semantic coherence
    - Include overlap for context continuity
    - Stay within token limits
    """
    
    # Separators in order of preference (most preferred first)
    SEPARATORS = [
        "\n\n\n",      # Section breaks
        "\n\n",         # Paragraph breaks
        "\n",           # Line breaks
        ". ",           # Sentences
        "? ",           # Questions
        "! ",           # Exclamations
        "; ",           # Semicolons
        ", ",           # Commas
        " ",            # Words
    ]
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
    ):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.processing.chunk_size
        self.chunk_overlap = chunk_overlap or settings.processing.chunk_overlap
        self.min_chunk_size = min_chunk_size or settings.processing.min_chunk_size
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 1 token ≈ 4 chars)."""
        return len(text) // 4
    
    def _split_by_separator(self, text: str, separator: str) -> list[str]:
        """Split text by separator, keeping the separator."""
        if separator == " ":
            return text.split(" ")
        
        parts = text.split(separator)
        # Re-add separator to end of each part (except last)
        result = []
        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                result.append(part + separator)
            else:
                result.append(part)
        return [p for p in result if p.strip()]
    
    def _recursive_split(
        self,
        text: str,
        separators: list[str],
    ) -> list[str]:
        """
        Recursively split text until chunks are small enough.
        """
        if self._estimate_tokens(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        if not separators:
            # Last resort: hard split by character count
            char_limit = self.chunk_size * 4
            chunks = []
            while text:
                chunks.append(text[:char_limit])
                text = text[char_limit:]
            return chunks
        
        # Try current separator
        separator = separators[0]
        if separator not in text:
            return self._recursive_split(text, separators[1:])
        
        parts = self._split_by_separator(text, separator)
        
        # Merge small parts, split large parts
        chunks = []
        current_chunk = ""
        
        for part in parts:
            part_tokens = self._estimate_tokens(part)
            current_tokens = self._estimate_tokens(current_chunk)
            
            if part_tokens > self.chunk_size:
                # Part is too large, need to split further
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                sub_chunks = self._recursive_split(part, separators[1:])
                chunks.extend(sub_chunks)
            
            elif current_tokens + part_tokens <= self.chunk_size:
                # Add to current chunk
                current_chunk += part
            
            else:
                # Current chunk is full, start new one
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """Add overlap between chunks for context continuity."""
        if len(chunks) <= 1:
            return chunks
        
        overlapped = []
        overlap_chars = self.chunk_overlap * 4  # Convert tokens to chars
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk: no prefix
                overlapped.append(chunk)
            else:
                # Get overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk
                
                # Find a clean break point in overlap
                last_space = overlap_text.rfind(' ')
                if last_space > 0:
                    overlap_text = overlap_text[last_space + 1:]
                
                overlapped.append(overlap_text + chunk)
        
        return overlapped
    
    def chunk(
        self,
        content: str,
        source_url: str,
        source_title: str,
    ) -> list[ContentChunk]:
        """
        Split content into chunks.
        
        Args:
            content: Text content to chunk
            source_url: Source URL for attribution
            source_title: Source title for attribution
            
        Returns:
            List of ContentChunk objects
        """
        if not content or not content.strip():
            return []
        
        logger.debug(f"Chunking content: {len(content)} chars")
        
        # Split into raw chunks
        raw_chunks = self._recursive_split(content, self.SEPARATORS)
        
        # Filter out too-small chunks
        filtered_chunks = [
            c for c in raw_chunks
            if self._estimate_tokens(c) >= self.min_chunk_size
        ]
        
        # Add overlap
        overlapped_chunks = self._add_overlap(filtered_chunks)
        
        # Create ContentChunk objects
        result = []
        for i, text in enumerate(overlapped_chunks):
            chunk = ContentChunk(
                id="",  # Will be generated in __post_init__
                source_url=source_url,
                source_title=source_title,
                content=text.strip(),
                chunk_index=i,
                total_chunks=len(overlapped_chunks),
            )
            result.append(chunk)
        
        logger.debug(f"Created {len(result)} chunks")
        return result
    
    def chunk_for_context(
        self,
        content: str,
        source_url: str,
        source_title: str,
        max_chunks: Optional[int] = None,
    ) -> list[ContentChunk]:
        """
        Chunk content for use in LLM context.
        
        Similar to chunk() but optimized for context window usage.
        """
        chunks = self.chunk(content, source_url, source_title)
        
        if max_chunks and len(chunks) > max_chunks:
            # Keep first chunk (usually has key info) and best middle chunks
            # Simple strategy: take every Nth chunk to stay within limit
            step = len(chunks) // max_chunks
            chunks = chunks[::step][:max_chunks]
        
        return chunks
    
    def estimate_total_tokens(self, chunks: list[ContentChunk]) -> int:
        """Estimate total tokens across all chunks."""
        return sum(c.token_count for c in chunks)
