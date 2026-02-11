"""
Memory API Schemas.

Pydantic models for memory-related API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryTypeEnum(str, Enum):
    """Types of memories."""
    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    HISTORY = "history"
    INSTRUCTION = "instruction"


class MemoryPriorityEnum(str, Enum):
    """Priority levels for memories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== Request Schemas ====================

class AddMemoryRequest(BaseModel):
    """Request to add a new memory."""
    user_id: str = Field(
        default="default",
        description="User identifier"
    )
    memory_type: MemoryTypeEnum = Field(
        default=MemoryTypeEnum.FACT,
        description="Type of memory"
    )
    key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Short key/title for the memory"
    )
    value: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Full memory content"
    )
    priority: MemoryPriorityEnum = Field(
        default=MemoryPriorityEnum.MEDIUM,
        description="Memory priority level"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "user123",
                    "memory_type": "preference",
                    "key": "source preference",
                    "value": "User prefers academic papers and peer-reviewed sources over news articles",
                    "priority": "high"
                }
            ]
        }
    }


class UpdateMemoryRequest(BaseModel):
    """Request to update an existing memory."""
    value: str | None = Field(
        default=None,
        max_length=2000,
        description="New memory content"
    )
    priority: MemoryPriorityEnum | None = Field(
        default=None,
        description="New priority level"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "value": "Updated: User now prefers recent sources from the last 2 years",
                    "priority": "critical"
                }
            ]
        }
    }


class SearchMemoriesRequest(BaseModel):
    """Request to search memories."""
    user_id: str = Field(
        default="default",
        description="User identifier"
    )
    query: str = Field(
        ...,
        min_length=1,
        description="Search query"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results"
    )


class ExtractMemoriesRequest(BaseModel):
    """Request to extract memories from query/context."""
    user_id: str = Field(
        default="default",
        description="User identifier"
    )
    query: str = Field(
        ...,
        min_length=1,
        description="Query to extract memories from"
    )
    context: str = Field(
        default="",
        description="Additional context"
    )
    session_id: str | None = Field(
        default=None,
        description="Source session ID"
    )
    store: bool = Field(
        default=False,
        description="Whether to persist extracted memories. When False, performs a dry-run (extract only)."
    )


class GetContextRequest(BaseModel):
    """Request to get memory context for research."""
    user_id: str = Field(
        default="default",
        description="User identifier"
    )
    query: str = Field(
        default="",
        description="Research query to find relevant memories"
    )
    max_memories: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum memories to include"
    )


# ==================== Response Schemas ====================

class MemoryResponse(BaseModel):
    """Single memory response."""
    memory_id: str = Field(description="Unique memory identifier")
    user_id: str = Field(description="User identifier")
    memory_type: MemoryTypeEnum = Field(description="Type of memory")
    key: str = Field(description="Memory key/title")
    value: str = Field(description="Memory content")
    priority: MemoryPriorityEnum = Field(description="Priority level")
    source_session: str | None = Field(description="Session that created this memory")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime | None = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(description="Last update timestamp")
    access_count: int = Field(default=0, description="Number of times accessed")
    is_active: bool = Field(default=True, description="Whether memory is active")
    
    @classmethod
    def from_memory(cls, memory) -> "MemoryResponse":
        """Create from UserMemory object."""
        return cls(
            memory_id=memory.memory_id,
            user_id=memory.user_id,
            memory_type=MemoryTypeEnum(memory.memory_type.value if hasattr(memory.memory_type, 'value') else memory.memory_type),
            key=memory.key,
            value=memory.value,
            priority=MemoryPriorityEnum(memory.priority.value if hasattr(memory.priority, 'value') else memory.priority),
            source_session=memory.source_session,
            metadata=memory.metadata,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            access_count=memory.access_count,
            is_active=memory.is_active
        )


class MemoryListResponse(BaseModel):
    """Response containing list of memories."""
    memories: list[MemoryResponse] = Field(description="List of memories")
    total: int = Field(description="Total number of memories")
    user_id: str = Field(description="User identifier")


class MemoryContextResponse(BaseModel):
    """Response containing memory context for research."""
    context_string: str = Field(description="Formatted context string for LLM")
    memories: list[MemoryResponse] = Field(description="Relevant memories")
    memory_count: int = Field(description="Number of memories included")
    user_id: str = Field(description="User identifier")


class MemoryExtractionResponse(BaseModel):
    """Response from memory extraction."""
    extracted_count: int = Field(description="Number of memories extracted")
    memories: list[MemoryResponse] = Field(description="Extracted memories")
    reasoning: str = Field(description="Explanation of extraction")
    user_id: str = Field(description="User identifier")


class MemoryStatsResponse(BaseModel):
    """Memory statistics response."""
    total_memories: int = Field(description="Total number of active memories")
    by_type: dict[str, int] = Field(description="Count by memory type")
    by_priority: dict[str, int] = Field(description="Count by priority level")
    user_id: str | None = Field(description="User identifier if filtered")


class MemoryDeleteResponse(BaseModel):
    """Response from memory deletion."""
    success: bool = Field(description="Whether deletion was successful")
    memory_id: str = Field(description="Deleted memory ID")
    message: str = Field(description="Status message")


class MemoryErrorResponse(BaseModel):
    """Error response for memory operations."""
    error: str = Field(description="Error message")
    code: str = Field(description="Error code")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
