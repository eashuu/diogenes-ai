"""
Fact extraction from content.

Uses LLM to extract key facts with source attribution.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.services.llm.base import LLMService
from src.services.llm.models import LLMConfig
from src.processing.models import ContentChunk, ExtractedFact
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ExtractedFactsResponse(BaseModel):
    """Schema for LLM fact extraction response."""
    
    facts: list[str] = Field(
        description="List of key facts extracted from the content"
    )


class FactExtractor:
    """
    Extracts key facts from content using LLM.
    
    Each fact is attributed to its source chunk for citation purposes.
    """
    
    EXTRACTION_PROMPT = """Extract the key facts from the following content.

Content:
{content}

Instructions:
1. Extract 3-7 key facts from this content
2. Each fact should be a single, clear statement
3. Focus on factual information, not opinions
4. Include specific data, numbers, or names when present
5. Make each fact self-contained and understandable

Return the facts as a JSON object with a "facts" array."""

    def __init__(
        self,
        llm_service: LLMService,
        model: Optional[str] = None,
    ):
        self.llm_service = llm_service
        self.model = model
    
    async def extract_facts(
        self,
        chunk: ContentChunk,
        max_facts: int = 7,
    ) -> list[ExtractedFact]:
        """
        Extract facts from a single chunk.
        
        Args:
            chunk: Content chunk to extract from
            max_facts: Maximum facts to extract
            
        Returns:
            List of ExtractedFact objects
        """
        logger.debug(f"Extracting facts from chunk {chunk.id}")
        
        try:
            # Build config with extraction model
            config = LLMConfig(
                model=self.model,
                temperature=0.0,
                max_tokens=1024,
            )
            
            # Use structured output
            response = await self.llm_service.generate_structured(
                prompt=self.EXTRACTION_PROMPT.format(content=chunk.content),
                output_schema=ExtractedFactsResponse,
                config=config,
            )
            
            # Convert to ExtractedFact objects
            facts = []
            for fact_text in response.facts[:max_facts]:
                fact = ExtractedFact(
                    id="",  # Generated in __post_init__
                    content=fact_text,
                    source_chunk_id=chunk.id,
                    source_url=chunk.source_url,
                    source_title=chunk.source_title,
                )
                facts.append(fact)
            
            logger.debug(f"Extracted {len(facts)} facts from chunk {chunk.id}")
            return facts
            
        except Exception as e:
            logger.error(f"Fact extraction failed for chunk {chunk.id}: {e}")
            return []
    
    async def extract_facts_batch(
        self,
        chunks: list[ContentChunk],
        max_facts_per_chunk: int = 5,
        max_total_facts: int = 30,
    ) -> list[ExtractedFact]:
        """
        Extract facts from multiple chunks.
        
        Args:
            chunks: List of chunks to process
            max_facts_per_chunk: Max facts per chunk
            max_total_facts: Max total facts to return
            
        Returns:
            Combined list of facts
        """
        import asyncio
        
        logger.info(f"Extracting facts from {len(chunks)} chunks")
        
        # Process chunks in parallel
        tasks = [
            self.extract_facts(chunk, max_facts_per_chunk)
            for chunk in chunks
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_facts = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Fact extraction failed: {result}")
                continue
            all_facts.extend(result)
        
        # Limit total facts
        if len(all_facts) > max_total_facts:
            all_facts = all_facts[:max_total_facts]
        
        logger.info(f"Extracted {len(all_facts)} total facts")
        return all_facts


class QuickFactExtractor:
    """
    Fast fact extraction without LLM calls.
    
    Uses heuristics to identify fact-like sentences.
    Good for when LLM calls would be too slow.
    """
    
    # Patterns that indicate factual content
    FACT_INDICATORS = [
        r'\d+%',           # Percentages
        r'\$[\d,]+',       # Dollar amounts
        r'\d{4}',          # Years
        r'\d+\s*(million|billion|trillion)',  # Large numbers
        r'according to',    # Citations
        r'research shows',
        r'studies show',
        r'data indicates',
    ]
    
    def __init__(self):
        import re
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.FACT_INDICATORS]
    
    def extract_facts(
        self,
        chunk: ContentChunk,
        max_facts: int = 5,
    ) -> list[ExtractedFact]:
        """
        Extract facts using heuristics.
        """
        sentences = self._split_sentences(chunk.content)
        
        # Score sentences by fact likelihood
        scored = []
        for sentence in sentences:
            score = self._score_sentence(sentence)
            if score > 0:
                scored.append((sentence, score))
        
        # Sort by score and take top N
        scored.sort(key=lambda x: x[1], reverse=True)
        top_sentences = scored[:max_facts]
        
        # Convert to facts
        facts = []
        for sentence, _ in top_sentences:
            fact = ExtractedFact(
                id="",
                content=sentence.strip(),
                source_chunk_id=chunk.id,
                source_url=chunk.source_url,
                source_title=chunk.source_title,
            )
            facts.append(fact)
        
        return facts
    
    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s for s in sentences if len(s) > 20]  # Filter short fragments
    
    def _score_sentence(self, sentence: str) -> float:
        """Score how likely a sentence is to be a fact."""
        score = 0.0
        
        # Check for fact indicators
        for pattern in self.patterns:
            if pattern.search(sentence):
                score += 1.0
        
        # Bonus for proper length
        words = len(sentence.split())
        if 10 <= words <= 40:
            score += 0.5
        
        # Bonus for ending with period
        if sentence.strip().endswith('.'):
            score += 0.2
        
        return score
