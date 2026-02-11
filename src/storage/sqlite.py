"""
SQLite-based Storage Implementation.

Provides persistent storage for sessions and cache using SQLite.
"""

import asyncio
import fnmatch
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from src.utils.logging import get_logger
from src.storage.base import CacheStore, SessionStore


logger = get_logger(__name__)


class SQLiteCache(CacheStore):
    """
    SQLite-backed cache implementation.
    
    Stores cached data with optional TTL.
    Uses JSON serialization for values.
    """
    
    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize SQLite cache.
        
        Args:
            db_path: Path to SQLite database file.
                     Defaults to ``settings.cache.database``.
        """
        if db_path is None:
            from src.config import get_settings
            db_path = get_settings().cache.database
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        self._lock = asyncio.Lock()
        
        # Stats
        self._hit_count = 0
        self._miss_count = 0
    
    async def _ensure_initialized(self):
        """Ensure database is initialized."""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            async with aiosqlite.connect(self.db_path) as db:
                # Enable WAL mode for better concurrent read/write performance
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 0
                    )
                """)
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)"
                )
                await db.commit()
            
            self._initialized = True
            logger.info(f"SQLite cache initialized at {self.db_path}")
    
    @asynccontextmanager
    async def _get_db(self):
        """Get database connection."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db
    
    async def get(self, key: str) -> Any | None:
        """Get a cached value."""
        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT value, expires_at FROM cache 
                WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                """,
                (key, datetime.utcnow().isoformat())
            )
            row = await cursor.fetchone()
            
            if row:
                self._hit_count += 1
                # Update access count
                await db.execute(
                    "UPDATE cache SET access_count = access_count + 1 WHERE key = ?",
                    (key,)
                )
                await db.commit()
                
                try:
                    return json.loads(row["value"])
                except json.JSONDecodeError:
                    return row["value"]
            
            self._miss_count += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta | None = None
    ) -> None:
        """Set a cached value."""
        expires_at = None
        if ttl:
            expires_at = (datetime.utcnow() + ttl).isoformat()
        
        # Serialize value
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = json.dumps(value)
        
        async with self._get_db() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, value_str, expires_at, datetime.utcnow().isoformat())
            )
            await db.commit()
    
    async def delete(self, key: str) -> bool:
        """Delete a cached value."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "DELETE FROM cache WHERE key = ?",
                (key,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT 1 FROM cache 
                WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                """,
                (key, datetime.utcnow().isoformat())
            )
            row = await cursor.fetchone()
            return row is not None
    
    async def clear(self) -> int:
        """Clear all cached values."""
        async with self._get_db() as db:
            cursor = await db.execute("DELETE FROM cache")
            await db.commit()
            return cursor.rowcount
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching a pattern."""
        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT key FROM cache 
                WHERE expires_at IS NULL OR expires_at > ?
                """,
                (datetime.utcnow().isoformat(),)
            )
            rows = await cursor.fetchall()
            
            all_keys = [row["key"] for row in rows]
            
            if pattern == "*":
                return all_keys
            
            return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
    
    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        async with self._get_db() as db:
            # Total entries
            cursor = await db.execute("SELECT COUNT(*) as count FROM cache")
            row = await cursor.fetchone()
            total = row["count"] if row else 0
            
            # Expired entries
            cursor = await db.execute(
                """
                SELECT COUNT(*) as count FROM cache 
                WHERE expires_at IS NOT NULL AND expires_at <= ?
                """,
                (datetime.utcnow().isoformat(),)
            )
            row = await cursor.fetchone()
            expired = row["count"] if row else 0
            
            # Size on disk
            size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        
        total_requests = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": hit_rate,
            "size_bytes": size_bytes
        }
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (datetime.utcnow().isoformat(),)
            )
            await db.commit()
            removed = cursor.rowcount
            
            if removed > 0:
                logger.info(f"Cleaned up {removed} expired cache entries")
            
            return removed


class SQLiteSessionStore(SessionStore):
    """
    SQLite-backed session storage.
    
    Stores research sessions with full state.
    """
    
    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize SQLite session store.
        
        Args:
            db_path: Path to SQLite database file.
                     Defaults to ``settings.session.database``.
        """
        if db_path is None:
            from src.config import get_settings
            db_path = get_settings().session.database
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def _ensure_initialized(self):
        """Ensure database is initialized."""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            async with aiosqlite.connect(self.db_path) as db:
                # Enable WAL mode for better concurrent read/write performance
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        query TEXT NOT NULL,
                        state TEXT NOT NULL,
                        status TEXT NOT NULL,
                        has_answer BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_created ON sessions(created_at DESC)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_query ON sessions(query)"
                )
                await db.commit()
            
            self._initialized = True
            logger.info(f"SQLite session store initialized at {self.db_path}")
    
    @asynccontextmanager
    async def _get_db(self):
        """Get database connection."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db
    
    def _row_to_dict(self, row) -> dict:
        """Convert row to session dict."""
        state = json.loads(row["state"]) if row["state"] else {}
        return {
            "session_id": row["session_id"],
            "query": row["query"],
            "state": state,
            "status": row["status"],
            "has_answer": bool(row["has_answer"]),
            "created_at": datetime.fromisoformat(row["created_at"]),
            "updated_at": datetime.fromisoformat(row["updated_at"])
        }
    
    async def get(self, key: str) -> dict | None:
        """Get a session by ID."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (key,)
            )
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    async def set(
        self,
        key: str,
        value: dict,
        ttl: timedelta | None = None
    ) -> None:
        """Set a session."""
        state = value.get("state", {})
        query = value.get("query", "")
        status = state.get("phase", "unknown")
        if hasattr(status, "value"):
            status = status.value
        has_answer = bool(state.get("final_answer"))
        
        state_json = json.dumps(state, default=str)
        now = datetime.utcnow().isoformat()
        
        async with self._get_db() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO sessions 
                (session_id, query, state, status, has_answer, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?),
                    ?)
                """,
                (key, query, state_json, status, has_answer, key, now, now)
            )
            await db.commit()
    
    async def delete(self, key: str) -> bool:
        """Delete a session."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (key,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def exists(self, key: str) -> bool:
        """Check if a session exists."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?",
                (key,)
            )
            row = await cursor.fetchone()
            return row is not None
    
    async def clear(self) -> int:
        """Clear all sessions."""
        async with self._get_db() as db:
            cursor = await db.execute("DELETE FROM sessions")
            await db.commit()
            return cursor.rowcount
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get session IDs matching a pattern."""
        async with self._get_db() as db:
            cursor = await db.execute("SELECT session_id FROM sessions")
            rows = await cursor.fetchall()
            
            all_keys = [row["session_id"] for row in rows]
            
            if pattern == "*":
                return all_keys
            
            return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
    
    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> list[dict]:
        """List sessions with pagination."""
        # Validate order_by to prevent SQL injection
        valid_columns = {"created_at", "updated_at", "query", "status"}
        if order_by not in valid_columns:
            order_by = "created_at"
        
        order_dir = "DESC" if order_desc else "ASC"
        
        async with self._get_db() as db:
            cursor = await db.execute(
                f"""
                SELECT * FROM sessions 
                ORDER BY {order_by} {order_dir}
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            rows = await cursor.fetchall()
            
            return [self._row_to_dict(row) for row in rows]
    
    async def get_by_query(self, query: str) -> list[dict]:
        """Find sessions by query text."""
        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT * FROM sessions 
                WHERE query LIKE ?
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (f"%{query}%",)
            )
            rows = await cursor.fetchall()
            
            return [self._row_to_dict(row) for row in rows]
    
    async def update_session(
        self,
        key: str,
        updates: dict
    ) -> bool:
        """Update a session with new data."""
        session = await self.get(key)
        if not session:
            return False
        
        # Merge updates
        session.update(updates)
        
        # Re-save
        await self.set(key, session)
        return True
    
    async def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        async with self._get_db() as db:
            # Total sessions
            cursor = await db.execute("SELECT COUNT(*) as count FROM sessions")
            row = await cursor.fetchone()
            total = row["count"] if row else 0
            
            # Sessions with answers
            cursor = await db.execute(
                "SELECT COUNT(*) as count FROM sessions WHERE has_answer = TRUE"
            )
            row = await cursor.fetchone()
            with_answers = row["count"] if row else 0
            
            # By status
            cursor = await db.execute(
                "SELECT status, COUNT(*) as count FROM sessions GROUP BY status"
            )
            rows = await cursor.fetchall()
            by_status = {row["status"]: row["count"] for row in rows}
        
        return {
            "total_sessions": total,
            "with_answers": with_answers,
            "by_status": by_status
        }
