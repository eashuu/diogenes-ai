"""
Memory API Routes.

Provides REST endpoints for managing user memories.
Similar to ChatGPT's memory feature.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from src.core.agents.memory import MemoryAgent
from src.storage.memory_store import MemoryStore, MemoryType, MemoryPriority
from src.api.schemas.memory import (
    AddMemoryRequest,
    UpdateMemoryRequest,
    SearchMemoriesRequest,
    ExtractMemoriesRequest,
    GetContextRequest,
    MemoryResponse,
    MemoryListResponse,
    MemoryContextResponse,
    MemoryExtractionResponse,
    MemoryStatsResponse,
    MemoryDeleteResponse,
    MemoryTypeEnum,
    MemoryPriorityEnum
)
from src.utils.logging import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory"])

# Singleton instances
_memory_store: MemoryStore | None = None
_memory_agent: MemoryAgent | None = None


def get_memory_store() -> MemoryStore:
    """Get or create memory store singleton."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store


def get_memory_agent() -> MemoryAgent:
    """Get or create memory agent singleton."""
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent(memory_store=get_memory_store())
    return _memory_agent


# ==================== CRUD Endpoints ====================

@router.post(
    "/",
    response_model=MemoryResponse,
    summary="Add a new memory",
    description="Store a new memory for a user (fact, preference, instruction, etc.)"
)
async def add_memory(request: AddMemoryRequest):
    """
    Add a new memory for a user.
    
    This is similar to ChatGPT's memory feature where you can store
    personal facts, preferences, and standing instructions.
    
    **Memory Types:**
    - `fact`: Personal facts about the user
    - `preference`: User preferences (sources, format, style)
    - `context`: Domain expertise or ongoing projects
    - `history`: Key insights from past research
    - `instruction`: Standing instructions for all research
    
    **Example:**
    ```json
    {
        "user_id": "user123",
        "memory_type": "preference",
        "key": "source preference",
        "value": "User prefers academic papers over news articles",
        "priority": "high"
    }
    ```
    """
    agent = get_memory_agent()
    
    memory = await agent.remember(
        user_id=request.user_id,
        key=request.key,
        value=request.value,
        memory_type=MemoryType(request.memory_type.value),
        priority=MemoryPriority(request.priority.value)
    )
    
    logger.info(f"Added memory for user {request.user_id}: {request.key}")
    return MemoryResponse.from_memory(memory)


@router.get(
    "/",
    response_model=MemoryListResponse,
    summary="List user memories",
    description="Get all memories for a user, optionally filtered by type"
)
async def list_memories(
    user_id: str = Query(default="default", description="User identifier"),
    memory_type: Optional[MemoryTypeEnum] = Query(default=None, description="Filter by memory type"),
    priority: Optional[MemoryPriorityEnum] = Query(default=None, description="Filter by priority"),
    session_id: Optional[str] = Query(default=None, description="Filter by source session ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum memories to return")
):
    """
    List all memories for a user.
    
    Can filter by memory type, priority level, and/or source session.
    Results are ordered by priority (critical first) then by access count.
    """
    store = get_memory_store()
    
    memories = await store.get_user_memories(
        user_id=user_id,
        memory_type=MemoryType(memory_type.value) if memory_type else None,
        priority=MemoryPriority(priority.value) if priority else None,
        session_id=session_id,
        limit=limit
    )
    
    return MemoryListResponse(
        memories=[MemoryResponse.from_memory(m) for m in memories],
        total=len(memories),
        user_id=user_id
    )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a specific memory",
    description="Retrieve a single memory by its ID"
)
async def get_memory(memory_id: str):
    """Get a specific memory by ID."""
    store = get_memory_store()
    
    memory = await store.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail=f"Memory not found: {memory_id}")
    
    return MemoryResponse.from_memory(memory)


@router.put(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update a memory",
    description="Update the value or priority of an existing memory"
)
async def update_memory(memory_id: str, request: UpdateMemoryRequest):
    """
    Update an existing memory.
    
    Can update the value and/or priority.
    """
    store = get_memory_store()
    
    memory = await store.update_memory(
        memory_id=memory_id,
        value=request.value,
        priority=MemoryPriority(request.priority.value) if request.priority else None
    )
    
    if not memory:
        raise HTTPException(status_code=404, detail=f"Memory not found: {memory_id}")
    
    logger.info(f"Updated memory: {memory_id}")
    return MemoryResponse.from_memory(memory)


@router.delete(
    "/{memory_id}",
    response_model=MemoryDeleteResponse,
    summary="Delete a memory",
    description="Soft delete a memory (can be restored)"
)
async def delete_memory(memory_id: str):
    """
    Delete a memory (soft delete).
    
    The memory is marked as inactive but not permanently removed.
    """
    store = get_memory_store()
    
    success = await store.delete(memory_id)
    
    return MemoryDeleteResponse(
        success=success,
        memory_id=memory_id,
        message="Memory deleted" if success else "Memory not found"
    )


# ==================== Search & Context Endpoints ====================

@router.post(
    "/search",
    response_model=MemoryListResponse,
    summary="Search memories",
    description="Search memories by text in key or value"
)
async def search_memories(request: SearchMemoriesRequest):
    """
    Search for memories containing specific text.
    
    Searches both the key and value fields.
    """
    store = get_memory_store()
    
    memories = await store.search_memories(
        user_id=request.user_id,
        search_text=request.query,
        limit=request.limit
    )
    
    return MemoryListResponse(
        memories=[MemoryResponse.from_memory(m) for m in memories],
        total=len(memories),
        user_id=request.user_id
    )


@router.post(
    "/context",
    response_model=MemoryContextResponse,
    summary="Get memory context",
    description="Get relevant memories formatted as context for research"
)
async def get_memory_context(request: GetContextRequest):
    """
    Get memories relevant to a research query.
    
    Returns a formatted context string suitable for injecting into
    LLM prompts, along with the individual memories.
    
    **Priority:**
    1. Critical and high priority memories
    2. User preferences and instructions
    3. Memories matching keywords in the query
    """
    agent = get_memory_agent()
    
    context = await agent._get_memory_context(
        user_id=request.user_id,
        query=request.query,
        max_memories=request.max_memories
    )
    
    return MemoryContextResponse(
        context_string=context.context_string,
        memories=[MemoryResponse.from_memory(m) for m in context.memories],
        memory_count=context.memory_count,
        user_id=request.user_id
    )


# ==================== AI-Powered Endpoints ====================

@router.post(
    "/extract",
    response_model=MemoryExtractionResponse,
    summary="Extract memories from text",
    description="Use AI to extract and store memories from query/context"
)
async def extract_memories(request: ExtractMemoriesRequest):
    """
    Use AI to automatically extract memories from text.
    
    The LLM analyzes the query and context to identify:
    - Personal facts about the user
    - Preferences for sources or format
    - Domain expertise or context
    - Standing instructions
    
    Extracted memories are automatically stored.
    """
    agent = get_memory_agent()
    
    result = await agent._extract_memories(
        user_id=request.user_id,
        query=request.query,
        context=request.context,
        session_id=request.session_id,
        store=request.store,
    )
    
    return MemoryExtractionResponse(
        extracted_count=len(result.extracted_memories),
        memories=[MemoryResponse.from_memory(m) for m in result.extracted_memories],
        reasoning=result.reasoning,
        user_id=request.user_id
    )


# ==================== Convenience Endpoints ====================

@router.post(
    "/preference",
    response_model=MemoryResponse,
    summary="Set a preference",
    description="Quickly add a user preference"
)
async def set_preference(
    user_id: str = Query(default="default"),
    key: str = Query(..., description="Preference key"),
    value: str = Query(..., description="Preference value")
):
    """
    Quick endpoint to set a user preference.
    
    **Example:**
    ```
    POST /api/v2/memory/preference?key=citation_style&value=APA
    ```
    """
    agent = get_memory_agent()
    
    memory = await agent.set_preference(
        user_id=user_id,
        key=key,
        value=value
    )
    
    return MemoryResponse.from_memory(memory)


@router.post(
    "/instruction",
    response_model=MemoryResponse,
    summary="Add a standing instruction",
    description="Add a standing instruction for all research"
)
async def add_instruction(
    user_id: str = Query(default="default"),
    instruction: str = Query(..., description="The instruction to remember")
):
    """
    Add a standing instruction that applies to all research.
    
    **Example:**
    ```
    POST /api/v2/memory/instruction?instruction=Always include citations in APA format
    ```
    """
    agent = get_memory_agent()
    
    memory = await agent.add_instruction(
        user_id=user_id,
        instruction=instruction
    )
    
    return MemoryResponse.from_memory(memory)


# ==================== Stats & Management ====================

@router.get(
    "/stats/{user_id}",
    response_model=MemoryStatsResponse,
    summary="Get memory statistics",
    description="Get statistics about a user's memories"
)
async def get_memory_stats(user_id: str):
    """Get statistics about a user's stored memories."""
    store = get_memory_store()
    
    stats = await store.get_stats(user_id=user_id)
    
    return MemoryStatsResponse(
        total_memories=stats["total_memories"],
        by_type=stats["by_type"],
        by_priority=stats["by_priority"],
        user_id=user_id
    )


@router.delete(
    "/user/{user_id}",
    response_model=MemoryDeleteResponse,
    summary="Clear all user memories",
    description="Delete all memories for a specific user"
)
async def clear_user_memories(user_id: str):
    """
    Clear all memories for a user.
    
    This is a soft delete - memories can potentially be restored.
    """
    store = get_memory_store()
    
    # Get all memories for user first
    memories = await store.get_user_memories(user_id=user_id, limit=1000)
    
    # Delete each one
    deleted_count = 0
    for memory in memories:
        if await store.delete(memory.memory_id):
            deleted_count += 1
    
    logger.info(f"Cleared {deleted_count} memories for user {user_id}")
    
    return MemoryDeleteResponse(
        success=True,
        memory_id=user_id,
        message=f"Deleted {deleted_count} memories for user {user_id}"
    )
