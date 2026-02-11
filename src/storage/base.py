"""
Storage Base Interfaces.

Abstract base classes for storage implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, TypeVar, Generic


T = TypeVar("T")


class BaseStore(ABC, Generic[T]):
    """
    Abstract base class for key-value stores.
    
    Provides a consistent interface for different storage backends.
    """
    
    @abstractmethod
    async def get(self, key: str) -> T | None:
        """
        Get a value by key.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: T,
        ttl: timedelta | None = None
    ) -> None:
        """
        Set a value by key.
        
        Args:
            key: The key to set
            value: The value to store
            ttl: Optional time-to-live
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a value by key.
        
        Args:
            key: The key to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists.
        
        Args:
            key: The key to check
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """
        Clear all entries.
        
        Returns:
            Number of entries cleared
        """
        pass
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> list[str]:
        """
        Get all keys matching a pattern.
        
        Args:
            pattern: Glob-style pattern
            
        Returns:
            List of matching keys
        """
        pass
    
    async def get_or_set(
        self,
        key: str,
        default_factory,
        ttl: timedelta | None = None
    ) -> T:
        """
        Get a value or set it using a factory function.
        
        Args:
            key: The key to get/set
            default_factory: Async callable that returns the default value
            ttl: Optional time-to-live for new values
            
        Returns:
            The existing or newly set value
        """
        value = await self.get(key)
        if value is not None:
            return value
        
        value = await default_factory()
        await self.set(key, value, ttl)
        return value


class CacheStore(BaseStore[Any]):
    """
    Cache-specific store interface.
    
    Adds cache-specific methods like stats and cleanup.
    """
    
    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hit_count, miss_count, size, etc.
        """
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        pass


class SessionStore(BaseStore[dict]):
    """
    Session-specific store interface.
    
    Manages research sessions with additional query methods.
    """
    
    @abstractmethod
    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> list[dict]:
        """
        List sessions with pagination.
        
        Args:
            limit: Maximum sessions to return
            offset: Offset for pagination
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            List of session dicts
        """
        pass
    
    @abstractmethod
    async def get_by_query(self, query: str) -> list[dict]:
        """
        Find sessions by query text.
        
        Args:
            query: Query text to search for
            
        Returns:
            List of matching sessions
        """
        pass
    
    @abstractmethod
    async def update_session(
        self,
        key: str,
        updates: dict
    ) -> bool:
        """
        Update a session with new data.
        
        Args:
            key: Session key
            updates: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        pass
