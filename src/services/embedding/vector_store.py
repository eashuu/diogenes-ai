"""
Vector Store Implementation.

Provides ChromaDB-based vector storage for semantic search.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from src.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    id: str
    content: str
    metadata: dict[str, Any]
    distance: float
    score: float  # Normalized similarity (1 - distance for cosine)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "metadata": self.metadata,
            "distance": self.distance,
            "score": self.score
        }


@dataclass
class CollectionStats:
    """Statistics for a vector collection."""
    name: str
    count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """
    Abstract base class for vector stores.
    
    Provides interface for storing and searching embeddings.
    """
    
    @abstractmethod
    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: Optional[list[dict]] = None
    ) -> int:
        """
        Add vectors to the store.
        
        Args:
            ids: Unique identifiers
            embeddings: Vector embeddings
            documents: Original text documents
            metadatas: Optional metadata dicts
            
        Returns:
            Number of vectors added
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
    async def delete(self, ids: list[str]) -> int:
        """
        Delete vectors by ID.
        
        Args:
            ids: IDs to delete
            
        Returns:
            Number deleted
        """
        pass
    
    @abstractmethod
    async def get(self, ids: list[str]) -> list[dict]:
        """
        Get vectors by ID.
        
        Args:
            ids: IDs to retrieve
            
        Returns:
            List of documents with embeddings
        """
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get total number of vectors."""
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """Clear all vectors."""
        pass


class ChromaVectorStore(VectorStore):
    """
    ChromaDB-based vector store implementation.
    
    Features:
    - Persistent storage to disk
    - Efficient similarity search
    - Metadata filtering
    - Multiple collections support
    """
    
    def __init__(
        self,
        collection_name: str = "diogenes_research",
        persist_directory: str = "data/chromadb",
        embedding_function = None
    ):
        """
        Initialize ChromaDB vector store.
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory for persistent storage
            embedding_function: Optional embedding function (for query-time embedding)
        """
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self._client = None
        self._collection = None
        self._embedding_function = embedding_function
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure ChromaDB client is initialized."""
        if self._initialized:
            return
        
        # Run sync initialization in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_sync)
        self._initialized = True
    
    def _init_sync(self):
        """Synchronous initialization."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            
            logger.info(f"ChromaDB initialized: {self.collection_name} ({self._collection.count()} vectors)")
            
        except ImportError:
            logger.error("ChromaDB not installed. Install with: pip install chromadb")
            raise ImportError("chromadb package required. Install with: pip install chromadb")
    
    async def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: Optional[list[dict]] = None
    ) -> int:
        """Add vectors to ChromaDB."""
        await self._ensure_initialized()
        
        if not ids:
            return 0
        
        # Ensure metadata exists for all documents
        if metadatas is None:
            metadatas = [{"added_at": datetime.utcnow().isoformat()} for _ in ids]
        else:
            # Add timestamp to existing metadata
            for m in metadatas:
                if "added_at" not in m:
                    m["added_at"] = datetime.utcnow().isoformat()
        
        # Run in thread pool since ChromaDB is sync
        loop = asyncio.get_event_loop()
        
        def _add():
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            return len(ids)
        
        count = await loop.run_in_executor(None, _add)
        logger.debug(f"Added {count} vectors to {self.collection_name}")
        return count
    
    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: Optional[list[dict]] = None
    ) -> int:
        """Upsert vectors (update or insert)."""
        await self._ensure_initialized()
        
        if not ids:
            return 0
        
        if metadatas is None:
            metadatas = [{"updated_at": datetime.utcnow().isoformat()} for _ in ids]
        
        loop = asyncio.get_event_loop()
        
        def _upsert():
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            return len(ids)
        
        return await loop.run_in_executor(None, _upsert)
    
    async def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search for similar vectors."""
        await self._ensure_initialized()
        
        loop = asyncio.get_event_loop()
        
        def _search():
            kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"]
            }
            if filter:
                kwargs["where"] = filter
            
            return self._collection.query(**kwargs)
        
        results = await loop.run_in_executor(None, _search)
        
        # Parse results
        search_results = []
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            for i, id_ in enumerate(ids):
                distance = distances[i] if i < len(distances) else 0.0
                search_results.append(SearchResult(
                    id=id_,
                    content=documents[i] if i < len(documents) else "",
                    metadata=metadatas[i] if i < len(metadatas) else {},
                    distance=distance,
                    score=1.0 - distance  # Convert distance to similarity
                ))
        
        return search_results
    
    async def search_with_text(
        self,
        query_text: str,
        embedding_service,
        n_results: int = 10,
        filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """
        Search using text query (auto-embeds).
        
        Args:
            query_text: Text to search for
            embedding_service: EmbeddingService instance
            n_results: Number of results
            filter: Optional metadata filter
            
        Returns:
            List of SearchResult objects
        """
        # Get query embedding
        result = await embedding_service.embed(query_text)
        return await self.search(
            query_embedding=result.embedding,
            n_results=n_results,
            filter=filter
        )
    
    async def delete(self, ids: list[str]) -> int:
        """Delete vectors by ID."""
        await self._ensure_initialized()
        
        if not ids:
            return 0
        
        loop = asyncio.get_event_loop()
        
        def _delete():
            self._collection.delete(ids=ids)
            return len(ids)
        
        return await loop.run_in_executor(None, _delete)
    
    async def get(self, ids: list[str]) -> list[dict]:
        """Get vectors by ID."""
        await self._ensure_initialized()
        
        if not ids:
            return []
        
        loop = asyncio.get_event_loop()
        
        def _get():
            return self._collection.get(
                ids=ids,
                include=["documents", "metadatas", "embeddings"]
            )
        
        results = await loop.run_in_executor(None, _get)
        
        documents = []
        if results and results.get("ids"):
            for i, id_ in enumerate(results["ids"]):
                doc = {
                    "id": id_,
                    "content": results["documents"][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                }
                if results.get("embeddings"):
                    doc["embedding"] = results["embeddings"][i]
                documents.append(doc)
        
        return documents
    
    async def count(self) -> int:
        """Get total number of vectors."""
        await self._ensure_initialized()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._collection.count())
    
    async def clear(self) -> int:
        """Clear all vectors from collection."""
        await self._ensure_initialized()
        
        current_count = await self.count()
        
        loop = asyncio.get_event_loop()
        
        def _clear():
            # Get all IDs and delete
            results = self._collection.get()
            if results and results.get("ids"):
                self._collection.delete(ids=results["ids"])
        
        await loop.run_in_executor(None, _clear)
        logger.info(f"Cleared {current_count} vectors from {self.collection_name}")
        return current_count
    
    async def get_stats(self) -> CollectionStats:
        """Get collection statistics."""
        await self._ensure_initialized()
        
        count = await self.count()
        
        return CollectionStats(
            name=self.collection_name,
            count=count,
            metadata={
                "persist_directory": str(self.persist_directory),
                "distance_metric": "cosine"
            }
        )
    
    async def list_collections(self) -> list[str]:
        """List all collections."""
        await self._ensure_initialized()
        
        loop = asyncio.get_event_loop()
        
        def _list():
            return [c.name for c in self._client.list_collections()]
        
        return await loop.run_in_executor(None, _list)
    
    async def create_collection(self, name: str) -> bool:
        """Create a new collection."""
        await self._ensure_initialized()
        
        loop = asyncio.get_event_loop()
        
        def _create():
            self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            return True
        
        return await loop.run_in_executor(None, _create)
    
    async def switch_collection(self, name: str):
        """Switch to a different collection."""
        await self._ensure_initialized()
        
        loop = asyncio.get_event_loop()
        
        def _switch():
            self._collection = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        
        await loop.run_in_executor(None, _switch)
        self.collection_name = name
        logger.info(f"Switched to collection: {name}")
