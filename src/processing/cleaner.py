"""
Content cleaning utilities.

Removes boilerplate, ads, navigation, and other non-content elements.
"""

import re
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ContentCleaner:
    """
    Cleans raw web content by removing boilerplate and formatting issues.
    """
    
    # Patterns to remove
    REMOVE_PATTERNS = [
        # Navigation and UI elements
        r'\[Skip to .*?\]',
        r'\[Menu\]',
        r'\[Search\]',
        r'\[Close\]',
        r'Cookie\s*(Policy|Notice|Consent).*?(?=\n\n|\Z)',
        
        # Social media
        r'(Share|Tweet|Pin|Follow)\s*(on|us)?\s*(Facebook|Twitter|LinkedIn|Instagram|Pinterest)?',
        r'Like\s+\d+',
        r'Share\s+\d+',
        
        # Ads and promotions
        r'Advertisement',
        r'Sponsored\s*(Content|Post)?',
        r'ADVERTISEMENT',
        
        # Common boilerplate
        r'All Rights Reserved\.?',
        r'©\s*\d{4}.*?(?=\n|\Z)',
        r'Terms\s*(of\s*)?(Service|Use)',
        r'Privacy\s*Policy',
        
        # Empty links and buttons
        r'\[.*?\]\(\s*\)',
        r'\[\s*\]',
    ]
    
    # Compile patterns
    COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in REMOVE_PATTERNS]
    
    def __init__(
        self,
        min_paragraph_length: int = 50,
        max_link_density: float = 0.5,
        remove_short_lines: bool = True,
    ):
        self.min_paragraph_length = min_paragraph_length
        self.max_link_density = max_link_density
        self.remove_short_lines = remove_short_lines
    
    def clean(self, content: str) -> str:
        """
        Clean content by removing boilerplate and formatting.
        
        Args:
            content: Raw content (markdown or text)
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
        
        original_length = len(content)
        
        # Apply removal patterns
        for pattern in self.COMPILED_PATTERNS:
            content = pattern.sub('', content)
        
        # Normalize whitespace
        content = self._normalize_whitespace(content)
        
        # Remove short lines if enabled
        if self.remove_short_lines:
            content = self._remove_short_lines(content)
        
        # Remove excessive blank lines
        content = self._remove_excessive_blanks(content)
        
        cleaned_length = len(content)
        logger.debug(
            f"Cleaned content: {original_length} -> {cleaned_length} chars "
            f"({100 - cleaned_length/max(original_length, 1)*100:.1f}% removed)"
        )
        
        return content.strip()
    
    def _normalize_whitespace(self, content: str) -> str:
        """Normalize various whitespace characters."""
        # Replace tabs with spaces
        content = content.replace('\t', ' ')
        
        # Replace multiple spaces with single space
        content = re.sub(r' {2,}', ' ', content)
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        return content
    
    def _remove_short_lines(self, content: str) -> str:
        """Remove lines that are too short to be meaningful content."""
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Keep empty lines (for paragraph separation)
            if not stripped:
                filtered_lines.append(line)
                continue
            
            # Keep headers (markdown)
            if stripped.startswith('#'):
                filtered_lines.append(line)
                continue
            
            # Keep list items
            if stripped.startswith(('-', '*', '•', '1.', '2.', '3.')):
                filtered_lines.append(line)
                continue
            
            # Keep if long enough
            if len(stripped) >= self.min_paragraph_length:
                filtered_lines.append(line)
                continue
            
            # Keep if it looks like a sentence (ends with punctuation)
            if stripped.endswith(('.', '!', '?', ':')):
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _remove_excessive_blanks(self, content: str) -> str:
        """Remove more than 2 consecutive blank lines."""
        return re.sub(r'\n{3,}', '\n\n', content)
    
    def extract_main_content(self, content: str) -> str:
        """
        Extract the main content section, removing headers/footers.
        
        This is a heuristic approach that looks for the densest
        content section.
        """
        paragraphs = content.split('\n\n')
        
        if len(paragraphs) <= 3:
            return content
        
        # Score each paragraph by content density
        scored = []
        for i, para in enumerate(paragraphs):
            # Score based on length and text characteristics
            words = len(para.split())
            has_sentences = bool(re.search(r'[.!?]', para))
            
            score = words
            if has_sentences:
                score *= 1.5
            
            scored.append((i, score, para))
        
        # Find the main content region (highest density cluster)
        # Simple approach: keep paragraphs with above-average score
        avg_score = sum(s[1] for s in scored) / len(scored) if scored else 0
        threshold = avg_score * 0.3  # Keep paragraphs above 30% of average
        
        main_content = [
            para for _, score, para in scored
            if score >= threshold
        ]
        
        return '\n\n'.join(main_content)
    
    def clean_for_embedding(self, content: str) -> str:
        """
        Clean content specifically for embedding/vector search.
        
        More aggressive cleaning for better semantic matching.
        """
        content = self.clean(content)
        
        # Remove markdown formatting
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)  # Links
        content = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', content)  # Bold/italic
        content = re.sub(r'^#{1,6}\s*', '', content, flags=re.MULTILINE)  # Headers
        content = re.sub(r'`[^`]+`', '', content)  # Code spans
        
        # Remove special characters
        content = re.sub(r'[^\w\s.,!?;:\-\'"()]', ' ', content)
        
        # Normalize whitespace again
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
