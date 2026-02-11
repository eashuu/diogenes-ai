"""
Embedding Service Package.

Provides embedding generation and vector storage functionality.
"""

from src.services.embedding.service import EmbeddingService
from src.services.embedding.vector_store import VectorStore, ChromaVectorStore

__all__ = [
    "EmbeddingService",
    "VectorStore",
    "ChromaVectorStore",
]
