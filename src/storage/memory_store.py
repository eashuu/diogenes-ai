"""
User Memory Storage.

Provides persistent storage for user memories (key facts, preferences, context)
similar to ChatGPT's memory feature.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiosqlite

from src.utils.logging import get_logger
from src.storage.base import BaseStore


logger = get_logger(__name__)


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    FACT = "fact"              # Personal facts about the user
    PREFERENCE = "preference"  # User preferences (sources, format, etc.)
    CONTEXT = "context"        # Research context/domain expertise
    HISTORY = "history"        # Key insights from past research
    INSTRUCTION = "instruction"  # Standing instructions for research


class MemoryPriority(str, Enum):
    """Priority levels for memories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserMemory:
    """Represents a single user memory."""
    
    def __init__(
        self,
        memory_id: str,
        user_id: str,
        memory_type: MemoryType,
        key: str,
        value: str,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        source_session: str | None = None,
        metadata: dict | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        access_count: int = 0,
        is_active: bool = True
    ):
        self.memory_id = memory_id
        self.user_id = user_id
        self.memory_type = memory_type
        self.key = key
        self.value = value
        self.priority = priority
        self.source_session = source_session
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.access_count = access_count
        self.is_active = is_active
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "memory_type": self.memory_type.value if isinstance(self.memory_type, MemoryType) else self.memory_type,
            "key": self.key,
            "value": self.value,
            "priority": self.priority.value if isinstance(self.priority, MemoryPriority) else self.priority,
            "source_session": self.source_session,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "access_count": self.access_count,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserMemory":
        """Create from dictionary."""
        return cls(
            memory_id=data["memory_id"],
            user_id=data["user_id"],
            memory_type=MemoryType(data["memory_type"]) if data.get("memory_type") else MemoryType.FACT,
            key=data["key"],
            value=data["value"],
            priority=MemoryPriority(data["priority"]) if data.get("priority") else MemoryPriority.MEDIUM,
            source_session=data.get("source_session"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            access_count=data.get("access_count", 0),
            is_active=data.get("is_active", True)
        )
    
    def to_context_string(self) -> str:
        """Convert to a string suitable for LLM context injection."""
        type_labels = {
            MemoryType.FACT: "User Fact",
            MemoryType.PREFERENCE: "User Preference",
            MemoryType.CONTEXT: "User Context",
            MemoryType.HISTORY: "Past Research",
            MemoryType.INSTRUCTION: "Standing Instruction"
        }
        label = type_labels.get(self.memory_type, "Memory")
        return f"[{label}] {self.key}: {self.value}"


class MemoryStore(BaseStore[UserMemory]):
    """
    SQLite-backed user memory storage.
    
    Stores persistent user memories similar to ChatGPT's memory feature.
    Supports multiple users, memory types, and priority levels.
    """
    
    DEFAULT_USER = "default"
    
    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize memory store.
        
        Args:
            db_path: Path to SQLite database file.
                     Defaults to ``settings.memory.database``.
        """
        if db_path is None:
            from src.config import get_settings
            db_path = get_settings().memory.database
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
                # Main memories table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        memory_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        priority TEXT DEFAULT 'medium',
                        source_session TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Indexes for efficient queries
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_memories ON memories(user_id, is_active)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(user_id, memory_type)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_priority ON memories(user_id, priority)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_key ON memories(user_id, key)"
                )
                
                await db.commit()
            
            self._initialized = True
            logger.info(f"Memory store initialized at {self.db_path}")
    
    @asynccontextmanager
    async def _get_db(self):
        """Get database connection."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db
    
    def _row_to_memory(self, row) -> UserMemory:
        """Convert database row to UserMemory object."""
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        return UserMemory(
            memory_id=row["memory_id"],
            user_id=row["user_id"],
            memory_type=MemoryType(row["memory_type"]),
            key=row["key"],
            value=row["value"],
            priority=MemoryPriority(row["priority"]),
            source_session=row["source_session"],
            metadata=metadata,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            access_count=row["access_count"],
            is_active=bool(row["is_active"])
        )
    
    async def get(self, key: str) -> UserMemory | None:
        """Get a memory by ID."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM memories WHERE memory_id = ? AND is_active = TRUE",
                (key,)
            )
            row = await cursor.fetchone()
            
            if row:
                # Update access count
                await db.execute(
                    "UPDATE memories SET access_count = access_count + 1 WHERE memory_id = ?",
                    (key,)
                )
                await db.commit()
                return self._row_to_memory(row)
            return None
    
    async def set(
        self,
        key: str,
        value: UserMemory,
        ttl=None  # Not used but required by interface
    ) -> None:
        """Set/update a memory."""
        metadata_json = json.dumps(value.metadata) if value.metadata else None
        now = datetime.utcnow().isoformat()
        
        async with self._get_db() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO memories 
                (memory_id, user_id, memory_type, key, value, priority, 
                 source_session, metadata, created_at, updated_at, access_count, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM memories WHERE memory_id = ?), ?),
                    ?, ?, ?)
                """,
                (
                    value.memory_id, value.user_id, 
                    value.memory_type.value if isinstance(value.memory_type, MemoryType) else value.memory_type,
                    value.key, value.value,
                    value.priority.value if isinstance(value.priority, MemoryPriority) else value.priority,
                    value.source_session, metadata_json,
                    value.memory_id, now,  # For COALESCE
                    now, value.access_count, value.is_active
                )
            )
            await db.commit()
    
    async def delete(self, key: str) -> bool:
        """Soft delete a memory (mark as inactive)."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "UPDATE memories SET is_active = FALSE, updated_at = ? WHERE memory_id = ?",
                (datetime.utcnow().isoformat(), key)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def hard_delete(self, key: str) -> bool:
        """Permanently delete a memory."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "DELETE FROM memories WHERE memory_id = ?",
                (key,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def exists(self, key: str) -> bool:
        """Check if a memory exists."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT 1 FROM memories WHERE memory_id = ? AND is_active = TRUE",
                (key,)
            )
            row = await cursor.fetchone()
            return row is not None
    
    async def clear(self) -> int:
        """Clear all memories (soft delete)."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "UPDATE memories SET is_active = FALSE, updated_at = ?",
                (datetime.utcnow().isoformat(),)
            )
            await db.commit()
            return cursor.rowcount
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all memory IDs."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT memory_id FROM memories WHERE is_active = TRUE"
            )
            rows = await cursor.fetchall()
            return [row["memory_id"] for row in rows]
    
    # ==================== User Memory Methods ====================
    
    async def add_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        key: str,
        value: str,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        source_session: str | None = None,
        metadata: dict | None = None
    ) -> UserMemory:
        """
        Add a new memory for a user.
        
        Args:
            user_id: User identifier
            memory_type: Type of memory
            key: Short key/title for the memory
            value: Full memory content
            priority: Memory priority level
            source_session: Session that created this memory
            metadata: Additional metadata
            
        Returns:
            Created UserMemory object
        """
        import uuid
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        
        memory = UserMemory(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=memory_type,
            key=key,
            value=value,
            priority=priority,
            source_session=source_session,
            metadata=metadata or {}
        )
        
        await self.set(memory_id, memory)
        logger.info(f"Added memory for user {user_id}: {key}")
        return memory
    
    async def get_user_memories(
        self,
        user_id: str,
        memory_type: MemoryType | None = None,
        priority: MemoryPriority | None = None,
        session_id: str | None = None,
        limit: int = 50,
        include_inactive: bool = False
    ) -> list[UserMemory]:
        """
        Get all memories for a user.
        
        Args:
            user_id: User identifier
            memory_type: Optional filter by type
            priority: Optional filter by priority
            session_id: Optional filter by source session ID
            limit: Maximum memories to return
            include_inactive: Whether to include soft-deleted memories
            
        Returns:
            List of UserMemory objects
        """
        query = "SELECT * FROM memories WHERE user_id = ?"
        params: list[Any] = [user_id]
        
        if not include_inactive:
            query += " AND is_active = TRUE"
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type.value if isinstance(memory_type, MemoryType) else memory_type)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority.value if isinstance(priority, MemoryPriority) else priority)
        
        if session_id:
            query += " AND source_session = ?"
            params.append(session_id)
        
        # Order by priority (critical first) then by access count
        priority_order = "CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END"
        query += f" ORDER BY {priority_order}, access_count DESC LIMIT ?"
        params.append(limit)
        
        async with self._get_db() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_memory(row) for row in rows]
    
    async def search_memories(
        self,
        user_id: str,
        search_text: str,
        limit: int = 20
    ) -> list[UserMemory]:
        """
        Search memories by key or value text.
        
        Args:
            user_id: User identifier
            search_text: Text to search for
            limit: Maximum results
            
        Returns:
            List of matching UserMemory objects
        """
        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT * FROM memories 
                WHERE user_id = ? AND is_active = TRUE
                AND (key LIKE ? OR value LIKE ?)
                ORDER BY access_count DESC
                LIMIT ?
                """,
                (user_id, f"%{search_text}%", f"%{search_text}%", limit)
            )
            rows = await cursor.fetchall()
            return [self._row_to_memory(row) for row in rows]
    
    async def get_context_memories(
        self,
        user_id: str,
        query: str | None = None,
        max_memories: int = 10
    ) -> list[UserMemory]:
        """
        Get memories relevant for research context.
        
        Prioritizes high-priority memories and those related to the query.
        
        Args:
            user_id: User identifier
            query: Optional research query to find relevant memories
            max_memories: Maximum memories to include
            
        Returns:
            List of relevant UserMemory objects
        """
        memories: list[UserMemory] = []
        
        # Always include critical and high priority memories
        high_priority = await self.get_user_memories(
            user_id=user_id,
            priority=MemoryPriority.CRITICAL,
            limit=5
        )
        memories.extend(high_priority)
        
        high_priority = await self.get_user_memories(
            user_id=user_id,
            priority=MemoryPriority.HIGH,
            limit=5
        )
        memories.extend(high_priority)
        
        # Include preferences and instructions
        preferences = await self.get_user_memories(
            user_id=user_id,
            memory_type=MemoryType.PREFERENCE,
            limit=5
        )
        for pref in preferences:
            if pref.memory_id not in [m.memory_id for m in memories]:
                memories.append(pref)
        
        instructions = await self.get_user_memories(
            user_id=user_id,
            memory_type=MemoryType.INSTRUCTION,
            limit=5
        )
        for inst in instructions:
            if inst.memory_id not in [m.memory_id for m in memories]:
                memories.append(inst)
        
        # If query provided, search for related memories
        if query:
            # Simple keyword matching - in future could use embeddings
            query_words = query.lower().split()
            related = await self.get_user_memories(user_id=user_id, limit=50)
            for mem in related:
                if mem.memory_id not in [m.memory_id for m in memories]:
                    mem_text = f"{mem.key} {mem.value}".lower()
                    if any(word in mem_text for word in query_words if len(word) > 3):
                        memories.append(mem)
        
        # Deduplicate and limit
        seen_ids = set()
        unique_memories = []
        for mem in memories:
            if mem.memory_id not in seen_ids:
                seen_ids.add(mem.memory_id)
                unique_memories.append(mem)
        
        return unique_memories[:max_memories]
    
    async def build_context_string(
        self,
        user_id: str,
        query: str | None = None,
        max_memories: int = 10
    ) -> str:
        """
        Build a context string for LLM prompt injection.
        
        Args:
            user_id: User identifier
            query: Optional research query
            max_memories: Maximum memories to include
            
        Returns:
            Formatted context string
        """
        memories = await self.get_context_memories(
            user_id=user_id,
            query=query,
            max_memories=max_memories
        )
        
        if not memories:
            return ""
        
        lines = ["### User Context (from memory)"]
        for mem in memories:
            lines.append(f"- {mem.to_context_string()}")
        
        return "\n".join(lines)
    
    async def update_memory(
        self,
        memory_id: str,
        value: str | None = None,
        priority: MemoryPriority | None = None,
        metadata: dict | None = None
    ) -> UserMemory | None:
        """
        Update an existing memory.
        
        Args:
            memory_id: Memory to update
            value: New value (optional)
            priority: New priority (optional)
            metadata: New metadata (optional, merged with existing)
            
        Returns:
            Updated UserMemory or None if not found
        """
        memory = await self.get(memory_id)
        if not memory:
            return None
        
        if value is not None:
            memory.value = value
        if priority is not None:
            memory.priority = priority
        if metadata is not None:
            memory.metadata.update(metadata)
        
        memory.updated_at = datetime.utcnow()
        await self.set(memory_id, memory)
        return memory
    
    async def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Get memory statistics.
        
        Args:
            user_id: Optional user to filter by
            
        Returns:
            Dictionary with memory statistics
        """
        async with self._get_db() as db:
            if user_id:
                # Stats for specific user
                cursor = await db.execute(
                    "SELECT COUNT(*) as total FROM memories WHERE user_id = ? AND is_active = TRUE",
                    (user_id,)
                )
            else:
                cursor = await db.execute(
                    "SELECT COUNT(*) as total FROM memories WHERE is_active = TRUE"
                )
            row = await cursor.fetchone()
            total = row["total"] if row else 0
            
            # By type
            if user_id:
                cursor = await db.execute(
                    """
                    SELECT memory_type, COUNT(*) as count 
                    FROM memories WHERE user_id = ? AND is_active = TRUE
                    GROUP BY memory_type
                    """,
                    (user_id,)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT memory_type, COUNT(*) as count 
                    FROM memories WHERE is_active = TRUE
                    GROUP BY memory_type
                    """
                )
            type_rows = await cursor.fetchall()
            by_type = {row["memory_type"]: row["count"] for row in type_rows}
            
            # By priority
            if user_id:
                cursor = await db.execute(
                    """
                    SELECT priority, COUNT(*) as count 
                    FROM memories WHERE user_id = ? AND is_active = TRUE
                    GROUP BY priority
                    """,
                    (user_id,)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT priority, COUNT(*) as count 
                    FROM memories WHERE is_active = TRUE
                    GROUP BY priority
                    """
                )
            priority_rows = await cursor.fetchall()
            by_priority = {row["priority"]: row["count"] for row in priority_rows}
            
            return {
                "total_memories": total,
                "by_type": by_type,
                "by_priority": by_priority,
                "user_id": user_id
            }
