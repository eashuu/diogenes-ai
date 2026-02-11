"""
Embedding Service.

Provides text embedding generation using Ollama's nomic-embed-text model.
Supports batch processing and caching.
"""

import asyncio
import hashlib
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import httpx
import numpy as np

from src.config import get_settings
from src.utils.logging import get_logger
from src.utils.retry import with_retry


logger = get_logger(__name__)


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    text: str
    embedding: list[float]
    model: str
    dimensions: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text[:100] + "..." if len(self.text) > 100 else self.text,
            "embedding_dimensions": self.dimensions,
            "model": self.model,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class BatchEmbeddingResult:
    """Result from batch embedding generation."""
    embeddings: list[EmbeddingResult]
    total_texts: int
    successful: int
    failed: int
    model: str
    elapsed_seconds: float
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_texts": self.total_texts,
            "successful": self.successful,
            "failed": self.failed,
            "model": self.model,
            "elapsed_seconds": self.elapsed_seconds
        }


class EmbeddingService:
    """
    Embedding service using Ollama's embedding models.
    
    Primary model: nomic-embed-text (768 dimensions)
    Fallback: mxbai-embed-large (1024 dimensions)
    
    Features:
    - Single and batch embedding generation
    - In-memory caching with LRU eviction
    - Automatic retry on failure
    - Dimensionality info tracking
    """
    
    # Default embedding model
    DEFAULT_MODEL = "nomic-embed-text"
    
    # Known model dimensions
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "snowflake-arctic-embed": 1024,
    }
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        max_cache_size: int = 10000,
    ):
        """
        Initialize embedding service.
        
        Args:
            base_url: Ollama API base URL
            model: Embedding model name
            timeout: Request timeout in seconds
            max_cache_size: Maximum cache entries
        """
        settings = get_settings()
        self.base_url = base_url or settings.llm.base_url
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout
        self.max_cache_size = max_cache_size
        
        self._client: Optional[httpx.AsyncClient] = None
        # Cache stores numpy arrays for memory efficiency (~6KB vs ~21.5KB per 768-dim vector)
        self._cache: dict[str, np.ndarray] = {}
        self._cache_order: list[str] = []  # For LRU
        
        # Stats
        self._total_requests = 0
        self._cache_hits = 0
        self._total_tokens = 0
    
    @property
    def dimensions(self) -> int:
        """Get embedding dimensions for current model."""
        return self.MODEL_DIMENSIONS.get(self.model, 768)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                base_url=self.base_url,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()[:16]
    
    def _add_to_cache(self, key: str, embedding: list[float]):
        """Add embedding to cache with LRU eviction.

        Stores as ``np.ndarray`` (float32) for ~3.5× memory savings over Python float lists.
        """
        if key in self._cache:
            # Move to end (most recently used)
            self._cache_order.remove(key)
            self._cache_order.append(key)
            return
        
        # Evict oldest if at capacity
        while len(self._cache) >= self.max_cache_size and self._cache_order:
            oldest_key = self._cache_order.pop(0)
            del self._cache[oldest_key]
        
        self._cache[key] = np.asarray(embedding, dtype=np.float32)
        self._cache_order.append(key)
    
    def _get_from_cache(self, key: str) -> Optional[np.ndarray]:
        """Get embedding from cache (returns numpy array or None)."""
        if key in self._cache:
            self._cache_hits += 1
            # Move to end (most recently used)
            self._cache_order.remove(key)
            self._cache_order.append(key)
            return self._cache[key]
        return None
    
    @with_retry(max_attempts=3, base_delay=1.0)
    async def _embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        client = await self._get_client()
        
        response = await client.post(
            "/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Embedding failed: {response.status_code} - {response.text}")
        
        data = response.json()
        embedding = data.get("embedding", [])
        
        if not embedding:
            raise Exception("No embedding returned from Ollama")
        
        return embedding
    
    async def embed(
        self,
        text: str,
        use_cache: bool = True
    ) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use/update cache
            
        Returns:
            EmbeddingResult with embedding vector
        """
        self._total_requests += 1
        
        # Normalize text
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text")
        
        # Check cache
        if use_cache:
            cache_key = self._cache_key(text)
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for embedding")
                return EmbeddingResult(
                    text=text,
                    embedding=cached.tolist(),
                    model=self.model,
                    dimensions=len(cached)
                )
        
        # Generate embedding
        embedding = await self._embed_single(text)
        
        # Update cache
        if use_cache:
            self._add_to_cache(cache_key, embedding)
        
        self._total_tokens += len(text.split())
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model,
            dimensions=len(embedding)
        )
    
    async def embed_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
        max_concurrent: int = 5
    ) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use/update cache
            max_concurrent: Maximum concurrent requests
            
        Returns:
            BatchEmbeddingResult with all embeddings
        """
        import time
        start_time = time.time()
        
        results: list[EmbeddingResult] = []
        failed = 0
        
        # Use semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def embed_with_semaphore(text: str) -> Optional[EmbeddingResult]:
            async with semaphore:
                try:
                    return await self.embed(text, use_cache=use_cache)
                except Exception as e:
                    logger.warning(f"Failed to embed text: {e}")
                    return None
        
        # Run all embeddings concurrently
        tasks = [embed_with_semaphore(text) for text in texts]
        completed = await asyncio.gather(*tasks)
        
        for result in completed:
            if result is not None:
                results.append(result)
            else:
                failed += 1
        
        elapsed = time.time() - start_time
        logger.info(f"Batch embedded {len(results)}/{len(texts)} texts in {elapsed:.2f}s")
        
        return BatchEmbeddingResult(
            embeddings=results,
            total_texts=len(texts),
            successful=len(results),
            failed=failed,
            model=self.model,
            elapsed_seconds=elapsed
        )
    
    async def embed_documents(
        self,
        documents: list[dict[str, Any]],
        text_key: str = "content",
        use_cache: bool = True
    ) -> list[dict[str, Any]]:
        """
        Embed a list of documents, adding embedding to each.
        
        Args:
            documents: List of document dicts
            text_key: Key containing text to embed
            use_cache: Whether to use cache
            
        Returns:
            Documents with 'embedding' field added
        """
        texts = [doc.get(text_key, "") for doc in documents]
        batch_result = await self.embed_batch(texts, use_cache=use_cache)
        
        # Match embeddings to documents
        embedded_docs = []
        for i, doc in enumerate(documents):
            doc_copy = dict(doc)
            if i < len(batch_result.embeddings):
                doc_copy["embedding"] = batch_result.embeddings[i].embedding
            embedded_docs.append(doc_copy)
        
        return embedded_docs
    
    async def similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Compute cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0-1)
        """
        result1 = await self.embed(text1)
        result2 = await self.embed(text2)
        
        # Vectorised cosine similarity via numpy
        vec_a = np.asarray(result1.embedding, dtype=np.float32)
        vec_b = np.asarray(result2.embedding, dtype=np.float32)
        
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    
    async def health_check(self) -> bool:
        """Check if embedding service is available."""
        try:
            result = await self.embed("test", use_cache=False)
            return len(result.embedding) > 0
        except Exception as e:
            logger.error(f"Embedding health check failed: {e}")
            return False
    
    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "cache_size": len(self._cache),
            "cache_hit_rate": self._cache_hits / max(1, self._total_requests),
            "estimated_tokens": self._total_tokens
        }
