"""
Conversation Threading and Branching.

Provides tree-structured conversation history with:
- Branching from any message
- Context chain retrieval
- Parent-child relationships
- Conversation export

Key feature for matching Perplexity AI's UX.
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from src.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ConversationNode:
    """A node in the conversation tree."""
    id: str
    session_id: str
    query: str
    response: str
    sources: list[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    children: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "query": self.query,
            "response": self.response,
            "sources": self.sources,
            "parent_id": self.parent_id,
            "children": self.children,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationNode":
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            query=data["query"],
            response=data["response"],
            sources=data.get("sources", []),
            parent_id=data.get("parent_id"),
            children=data.get("children", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            metadata=data.get("metadata", {})
        )


@dataclass
class ConversationTreeInfo:
    """Summary information about a conversation tree."""
    root_id: str
    session_id: str
    total_nodes: int
    max_depth: int
    branch_count: int
    created_at: datetime
    last_activity: datetime
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "root_id": self.root_id,
            "session_id": self.session_id,
            "total_nodes": self.total_nodes,
            "max_depth": self.max_depth,
            "branch_count": self.branch_count,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class ConversationTree:
    """
    Manages branching conversation history.
    
    Provides:
    - Tree-structured message storage
    - Branching from any node
    - Context chain retrieval for follow-ups
    - Full tree export
    """
    
    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize conversation tree storage.
        
        Args:
            db_path: Path to SQLite database file.
                     Defaults to ``settings.conversation.database``.
        """
        if db_path is None:
            from src.config import get_settings
            db_path = get_settings().conversation.database
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
                    CREATE TABLE IF NOT EXISTS conversation_nodes (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        parent_id TEXT,
                        query TEXT NOT NULL,
                        response TEXT NOT NULL,
                        sources TEXT DEFAULT '[]',
                        children TEXT DEFAULT '[]',
                        metadata TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (parent_id) REFERENCES conversation_nodes(id)
                    )
                """)
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_session ON conversation_nodes(session_id)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_parent ON conversation_nodes(parent_id)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_created ON conversation_nodes(created_at DESC)"
                )
                await db.commit()
            
            self._initialized = True
            logger.info(f"Conversation tree storage initialized at {self.db_path}")
    
    @asynccontextmanager
    async def _get_db(self):
        """Get database connection."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db
    
    def _row_to_node(self, row) -> ConversationNode:
        """Convert database row to ConversationNode."""
        return ConversationNode(
            id=row["id"],
            session_id=row["session_id"],
            query=row["query"],
            response=row["response"],
            sources=json.loads(row["sources"]) if row["sources"] else [],
            parent_id=row["parent_id"],
            children=json.loads(row["children"]) if row["children"] else [],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
    
    async def create_node(
        self,
        session_id: str,
        query: str,
        response: str,
        sources: list[str] = None,
        parent_id: Optional[str] = None,
        metadata: dict = None,
        node_id: Optional[str] = None
    ) -> ConversationNode:
        """
        Create a new conversation node.
        
        Args:
            session_id: Session this node belongs to
            query: User's query
            response: Research response
            sources: List of source URLs
            parent_id: Optional parent node ID (for branching)
            metadata: Additional metadata
            node_id: Optional specific node ID
            
        Returns:
            Created ConversationNode
        """
        node_id = node_id or str(uuid.uuid4())
        sources = sources or []
        metadata = metadata or {}
        
        async with self._get_db() as db:
            # Insert the new node
            await db.execute(
                """
                INSERT INTO conversation_nodes 
                (id, session_id, parent_id, query, response, sources, children, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id,
                    session_id,
                    parent_id,
                    query,
                    response,
                    json.dumps(sources),
                    json.dumps([]),
                    json.dumps(metadata),
                    datetime.utcnow().isoformat()
                )
            )
            
            # Update parent's children list atomically if this is a branch
            if parent_id:
                # Atomic append: avoids read-modify-write race by doing the
                # JSON array mutation in-place within a single SQL UPDATE.
                await db.execute(
                    """
                    UPDATE conversation_nodes 
                    SET children = json_insert(
                        CASE WHEN children IS NULL OR children = '' THEN '[]' ELSE children END,
                        '$[#]', ?
                    )
                    WHERE id = ?
                    """,
                    (node_id, parent_id)
                )
            
            await db.commit()
        
        return ConversationNode(
            id=node_id,
            session_id=session_id,
            query=query,
            response=response,
            sources=sources,
            parent_id=parent_id,
            children=[],
            created_at=datetime.utcnow(),
            metadata=metadata
        )
    
    async def get_node(self, node_id: str) -> Optional[ConversationNode]:
        """Get a single node by ID."""
        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM conversation_nodes WHERE id = ?",
                (node_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_node(row)
            return None
    
    async def branch_from(
        self,
        node_id: str,
        new_query: str,
        new_response: str,
        sources: list[str] = None,
        metadata: dict = None
    ) -> Optional[ConversationNode]:
        """
        Create a new branch from an existing node.
        
        Args:
            node_id: The node to branch from
            new_query: New query for the branch
            new_response: Response for the new branch
            sources: Sources for the new node
            metadata: Additional metadata
            
        Returns:
            New ConversationNode, or None if parent not found
        """
        parent = await self.get_node(node_id)
        if not parent:
            logger.warning(f"Cannot branch: node {node_id} not found")
            return None
        
        return await self.create_node(
            session_id=parent.session_id,
            query=new_query,
            response=new_response,
            sources=sources,
            parent_id=node_id,
            metadata=metadata
        )
    
    async def get_context_chain(
        self,
        node_id: str,
        max_depth: int = 5
    ) -> list[ConversationNode]:
        """
        Get conversation history up to current node.
        
        Traverses parent pointers to build context chain.
        
        Args:
            node_id: Current node ID
            max_depth: Maximum number of parent nodes to retrieve
            
        Returns:
            List of ConversationNodes from oldest to newest
        """
        chain = []
        current_id = node_id
        
        async with self._get_db() as db:
            for _ in range(max_depth + 1):  # +1 to include current node
                cursor = await db.execute(
                    "SELECT * FROM conversation_nodes WHERE id = ?",
                    (current_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    break
                
                node = self._row_to_node(row)
                chain.append(node)
                
                if not node.parent_id:
                    break
                    
                current_id = node.parent_id
        
        # Return oldest first
        return list(reversed(chain))
    
    async def get_tree(self, session_id: str) -> list[ConversationNode]:
        """
        Get all nodes in a conversation tree.
        
        Args:
            session_id: Session ID to get tree for
            
        Returns:
            List of all ConversationNodes in the tree
        """
        async with self._get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM conversation_nodes WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            )
            rows = await cursor.fetchall()
            
            return [self._row_to_node(row) for row in rows]
    
    async def get_root_node(self, session_id: str) -> Optional[ConversationNode]:
        """Get the root node (first message) of a conversation."""
        async with self._get_db() as db:
            cursor = await db.execute(
                """
                SELECT * FROM conversation_nodes 
                WHERE session_id = ? AND parent_id IS NULL
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (session_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_node(row)
            return None
    
    async def get_tree_info(self, session_id: str) -> Optional[ConversationTreeInfo]:
        """
        Get summary information about a conversation tree.
        
        Args:
            session_id: Session ID
            
        Returns:
            ConversationTreeInfo or None if session not found
        """
        nodes = await self.get_tree(session_id)
        if not nodes:
            return None
        
        root = None
        max_depth = 0
        branch_count = 0
        last_activity = nodes[0].created_at
        
        # Calculate tree metrics
        depth_cache = {}
        
        for node in nodes:
            if node.parent_id is None:
                root = node
                depth_cache[node.id] = 0
            else:
                parent_depth = depth_cache.get(node.parent_id, 0)
                depth_cache[node.id] = parent_depth + 1
                max_depth = max(max_depth, depth_cache[node.id])
            
            # Count branches (nodes with multiple children)
            if len(node.children) > 1:
                branch_count += len(node.children) - 1
            
            if node.created_at > last_activity:
                last_activity = node.created_at
        
        if not root:
            return None
        
        return ConversationTreeInfo(
            root_id=root.id,
            session_id=session_id,
            total_nodes=len(nodes),
            max_depth=max_depth,
            branch_count=branch_count,
            created_at=root.created_at,
            last_activity=last_activity
        )
    
    async def delete_node(self, node_id: str, recursive: bool = True) -> int:
        """
        Delete a node and optionally its descendants.
        
        Args:
            node_id: Node ID to delete
            recursive: If True, delete all descendants too
            
        Returns:
            Number of nodes deleted
        """
        deleted = 0
        
        async with self._get_db() as db:
            if recursive:
                # Get all descendants first
                to_delete = [node_id]
                idx = 0
                
                while idx < len(to_delete):
                    cursor = await db.execute(
                        "SELECT id FROM conversation_nodes WHERE parent_id = ?",
                        (to_delete[idx],)
                    )
                    rows = await cursor.fetchall()
                    to_delete.extend(row["id"] for row in rows)
                    idx += 1
                
                # Delete all nodes
                for nid in to_delete:
                    await db.execute(
                        "DELETE FROM conversation_nodes WHERE id = ?",
                        (nid,)
                    )
                    deleted += 1
            else:
                # Just delete this node
                cursor = await db.execute(
                    "DELETE FROM conversation_nodes WHERE id = ?",
                    (node_id,)
                )
                deleted = cursor.rowcount
            
            # Update parent's children list
            cursor = await db.execute(
                "SELECT id, children FROM conversation_nodes"
            )
            rows = await cursor.fetchall()
            
            for row in rows:
                children = json.loads(row["children"]) if row["children"] else []
                if node_id in children:
                    children.remove(node_id)
                    await db.execute(
                        "UPDATE conversation_nodes SET children = ? WHERE id = ?",
                        (json.dumps(children), row["id"])
                    )
            
            await db.commit()
        
        return deleted
    
    async def export_tree(self, session_id: str) -> dict[str, Any]:
        """
        Export full conversation tree for sharing/saving.
        
        Args:
            session_id: Session to export
            
        Returns:
            Dictionary with tree structure
        """
        nodes = await self.get_tree(session_id)
        info = await self.get_tree_info(session_id)
        
        return {
            "session_id": session_id,
            "exported_at": datetime.utcnow().isoformat(),
            "info": info.to_dict() if info else None,
            "nodes": [node.to_dict() for node in nodes]
        }
    
    async def get_formatted_context(
        self,
        node_id: str,
        max_depth: int = 3
    ) -> str:
        """
        Get formatted conversation context for LLM.
        
        Args:
            node_id: Current node ID
            max_depth: How many previous messages to include
            
        Returns:
            Formatted string for LLM context
        """
        chain = await self.get_context_chain(node_id, max_depth)
        
        if not chain:
            return ""
        
        lines = ["Previous conversation:"]
        for i, node in enumerate(chain[:-1]):  # Exclude current node
            lines.append(f"\nQ{i+1}: {node.query}")
            # Truncate long responses
            response = node.response[:500] + "..." if len(node.response) > 500 else node.response
            lines.append(f"A{i+1}: {response}")
        
        return "\n".join(lines)


# Singleton instance
_conversation_tree: Optional[ConversationTree] = None


def get_conversation_tree() -> ConversationTree:
    """Get the global ConversationTree instance."""
    global _conversation_tree
    if _conversation_tree is None:
        _conversation_tree = ConversationTree()
    return _conversation_tree
