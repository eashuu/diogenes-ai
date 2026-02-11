"""
Research API Routes.

Handles research requests, streaming, and session management.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from src.config import get_settings
from src.utils.logging import get_logger
from src.utils.exceptions import DiogenesError
from src.api.schemas import (
    ResearchRequest,
    FollowUpRequest,
    ResearchResponse,
    ResearchStartResponse,
    ResearchAnswer,
    ResearchTiming,
    Source,
    ResearchStatus,
    SSEEventType,
    SessionInfo,
    SessionListResponse
)
from src.core.agent import ResearchAgent, AgentPhase
from src.core.agent.modes import SearchMode
from src.storage import SQLiteSessionStore


logger = get_logger(__name__)
router = APIRouter(prefix="/research", tags=["research"])

# Persistent session storage (SQLite-backed)
_session_store: SQLiteSessionStore | None = None

# Research concurrency gate (asyncio.Semaphore, lazily initialized)
_research_semaphore: asyncio.Semaphore | None = None


def _get_research_semaphore() -> asyncio.Semaphore:
    """Get or create the research concurrency semaphore."""
    global _research_semaphore
    if _research_semaphore is None:
        settings = get_settings()
        _research_semaphore = asyncio.Semaphore(settings.api.max_concurrent_research)
        logger.info(f"Research semaphore initialized: max_concurrent={settings.api.max_concurrent_research}")
    return _research_semaphore


def _get_session_store() -> SQLiteSessionStore:
    """Get or lazily initialise the session store."""
    global _session_store
    if _session_store is None:
        settings = get_settings()
        _session_store = SQLiteSessionStore(settings.session.database)
    return _session_store


def _serialize_state(state: dict) -> dict:
    """Return a JSON-safe shallow copy of agent state.

    Complex objects such as *citation_map* (which has a ``.sources``
    attribute containing rich Python objects) are flattened to plain
    dicts so that ``json.dumps`` in the session store preserves them.
    """
    serialized = dict(state)

    # Flatten citation_map to a plain dict
    citation_map = serialized.get("citation_map")
    if citation_map and hasattr(citation_map, "sources"):
        sources_data = {}
        for url, src in citation_map.sources.items():
            try:
                qs = float(getattr(src, "quality_score", 0.0) or 0.0)
            except Exception:
                qs = 0.0
            sources_data[url] = {
                "citation_index": getattr(src, "citation_index", 0),
                "title": getattr(src, "title", ""),
                "url": getattr(src, "url", url),
                "domain": getattr(src, "domain", ""),
                "favicon_url": getattr(src, "favicon_url", None),
                "quality_score": max(0.0, min(1.0, qs)),
            }
        serialized["citation_map"] = {"sources": sources_data}

    # Ensure phase is a plain string
    phase = serialized.get("phase")
    if hasattr(phase, "value"):
        serialized["phase"] = phase.value

    return serialized


def _phase_to_status(phase) -> ResearchStatus:
    """Convert agent phase to API status.

    *phase* may be an ``AgentPhase`` enum instance **or** a plain string
    (e.g. when the state was deserialized from SQLite storage).
    """
    mapping = {
        AgentPhase.PLANNING: ResearchStatus.PLANNING,
        AgentPhase.SEARCHING: ResearchStatus.SEARCHING,
        AgentPhase.CRAWLING: ResearchStatus.CRAWLING,
        AgentPhase.PROCESSING: ResearchStatus.PROCESSING,
        AgentPhase.REFLECTING: ResearchStatus.REFLECTING,
        AgentPhase.SYNTHESIZING: ResearchStatus.SYNTHESIZING,
        AgentPhase.COMPLETE: ResearchStatus.COMPLETE,
        AgentPhase.ERROR: ResearchStatus.ERROR
    }
    # Try direct lookup first (works for AgentPhase enum instances)
    result = mapping.get(phase)
    if result is not None:
        return result

    # Attempt to reconstruct enum from string (AgentPhase is str-based)
    if isinstance(phase, str):
        try:
            return mapping.get(AgentPhase(phase), ResearchStatus.PENDING)
        except ValueError:
            pass

    return ResearchStatus.PENDING


def _build_response(session_id: str, state: dict, query: str) -> ResearchResponse:
    """Build response from agent state."""
    # Extract timing
    timing_raw = state.get("timing", {})
    total_ms = int(sum(timing_raw.values()) * 1000)
    
    timing = ResearchTiming(
        planning_ms=int(timing_raw.get("planning", 0) * 1000) or None,
        search_ms=int(timing_raw.get("search", 0) * 1000) or None,
        crawl_ms=int(timing_raw.get("crawl", 0) * 1000) or None,
        processing_ms=int(timing_raw.get("processing", 0) * 1000) or None,
        synthesis_ms=int(timing_raw.get("synthesis", 0) * 1000) or None,
        total_ms=total_ms
    )
    
    # Extract answer
    answer_content = state.get("answer_with_citations") or state.get("final_answer", "")
    answer = ResearchAnswer(
        content=answer_content,
        word_count=len(answer_content.split()),
        has_citations="[" in answer_content and "]" in answer_content
    ) if answer_content else None
    
    # Extract sources — handle both live objects and serialized dicts
    sources = []
    citation_map = state.get("citation_map")
    if citation_map:
        # Determine the sources dict (live object vs deserialized dict)
        if hasattr(citation_map, "sources"):
            sources_dict = citation_map.sources  # live CitationMap object
        elif isinstance(citation_map, dict) and "sources" in citation_map:
            sources_dict = citation_map["sources"]  # deserialized from SQLite
        else:
            sources_dict = {}

        for url, src in sources_dict.items():
            if isinstance(src, dict):
                # Deserialized dict format (from SQLiteSessionStore)
                qs = float(src.get("quality_score", 0.0) or 0.0)
                qs = max(0.0, min(1.0, qs))
                sources.append(Source(
                    index=src.get("citation_index", 0),
                    title=src.get("title", ""),
                    url=src.get("url", url),
                    domain=src.get("domain", ""),
                    favicon_url=src.get("favicon_url"),
                    quality_score=qs,
                ))
            else:
                # Live Python object
                try:
                    qs = float(getattr(src, "quality_score", 0.0) or 0.0)
                except Exception:
                    qs = 0.0
                if qs < 0.0 or qs > 1.0:
                    logger.warning(
                        f"Source {src.url} has out-of-range quality_score={qs}. Clamping to [0,1]."
                    )
                qs = max(0.0, min(1.0, qs))
                sources.append(Source(
                    index=src.citation_index,
                    title=src.title,
                    url=src.url,
                    domain=src.domain,
                    favicon_url=src.favicon_url,
                    quality_score=qs,
                ))
    
    return ResearchResponse(
        session_id=session_id,
        query=query,
        status=_phase_to_status(state.get("phase", AgentPhase.COMPLETE)),
        answer=answer,
        sources=sorted(sources, key=lambda s: s.index),
        timing=timing,
        errors=state.get("errors", []),
        created_at=datetime.utcnow()
    )


async def _run_research(
    session_id: str,
    query: str,
    mode: str = "balanced",
    max_iterations: int = None
) -> dict:
    """Run research and store results. Gated by concurrency semaphore."""
    async with _get_research_semaphore():
        try:
            # Convert mode string to SearchMode enum
            try:
                mode_enum = SearchMode[mode.upper()]
            except KeyError:
                logger.warning(f"Invalid mode '{mode}', falling back to BALANCED")
                mode_enum = SearchMode.BALANCED
            agent = ResearchAgent(mode=mode_enum, max_iterations=max_iterations)
            state = await agent.research(query, session_id)
            
            # Store session (serialized for SQLite)
            store = _get_session_store()
            await store.set(session_id, {
                "state": _serialize_state(state),
                "query": query,
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Research error for session {session_id}: {e}")
            store = _get_session_store()
            await store.set(session_id, {
                "state": {"phase": AgentPhase.ERROR.value, "errors": [{"error": str(e)}]},
                "query": query,
            })
            raise


@router.post("/", response_model=ResearchResponse)
async def create_research(request: ResearchRequest):
    """
    Start a new research query (blocking).
    
    This endpoint runs the complete research process and returns
    the final result. For streaming updates, use the /stream endpoint.
    """
    session_id = str(uuid.uuid4())
    
    logger.info(f"Starting research: {request.query[:50]}... (session: {session_id})")
    
    try:
        state = await _run_research(
            session_id=session_id,
            query=request.query,
            mode=request.mode,
            max_iterations=request.max_iterations
        )
        
        return _build_response(session_id, state, request.query)
        
    except DiogenesError as e:
        logger.error(f"Research failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Research failed unexpectedly")


@router.post("/stream")
async def stream_research(request: ResearchRequest):
    """
    Start research with SSE streaming.
    
    Returns an event stream with progress updates.
    Events: status, planning, search, crawl, processing, 
            reflection, synthesis, sources, complete, error
    """
    session_id = str(uuid.uuid4())
    settings = get_settings()
    
    logger.info(f"Starting streaming research: {request.query[:50]}... (session: {session_id})")
    
    async def event_generator() -> AsyncGenerator[dict, None]:
        async with _get_research_semaphore():
            try:
                # Send initial status
                yield {
                    "event": SSEEventType.STATUS.value,
                    "data": json.dumps({
                        "session_id": session_id,
                        "phase": ResearchStatus.PENDING.value,
                        "message": "Research starting..."
                    })
                }
                
                # Convert mode string to SearchMode enum
                mode_enum = SearchMode[request.mode.upper()]
                agent = ResearchAgent(mode=mode_enum, max_iterations=request.max_iterations)
                
                # Stream through agent execution
                async for update in agent.research_stream(request.query, session_id):
                    node = update.get("node", "")
                    phase = update.get("phase", AgentPhase.PLANNING)
                    events = update.get("events", [])
                    state = update.get("state", {})
                    
                    # Send phase status
                    yield {
                        "event": SSEEventType.STATUS.value,
                        "data": json.dumps({
                            "phase": _phase_to_status(phase).value,
                            "node": node
                        })
                    }
                    
                    # Send specific events
                    for event in events:
                        event_type = event.get("type", "status")
                        event_data = event.get("data", {})
                        
                        # Map internal events to SSE events
                        if event_type == "planning_complete":
                            yield {
                                "event": SSEEventType.PLANNING.value,
                                "data": json.dumps(event_data)
                            }
                        elif event_type == "search_complete":
                            yield {
                                "event": SSEEventType.SEARCH.value,
                                "data": json.dumps(event_data)
                            }
                        elif event_type == "crawl_complete":
                            yield {
                                "event": SSEEventType.CRAWL.value,
                                "data": json.dumps(event_data)
                            }
                        elif event_type == "processing_complete":
                            yield {
                                "event": SSEEventType.PROCESSING.value,
                                "data": json.dumps(event_data)
                            }
                        elif event_type == "reflection_complete":
                            yield {
                                "event": SSEEventType.REFLECTION.value,
                                "data": json.dumps(event_data)
                            }
                        elif event_type == "synthesis_complete":
                            yield {
                                "event": SSEEventType.SYNTHESIS.value,
                                "data": json.dumps(event_data)
                            }
                    
                    # Persist latest state to SQLite
                    store = _get_session_store()
                    await store.set(session_id, {
                        "state": _serialize_state(state),
                        "query": request.query,
                    })
                    
                    # Small delay for UI updates
                    await asyncio.sleep(0.1)
                
                # Use the last live state (full object fidelity)
                final_state = state  # from the last iteration of the loop above
                
                # Send sources — handle both live objects and serialized dicts
                citation_map = final_state.get("citation_map")
                if citation_map:
                    if hasattr(citation_map, "sources"):
                        sources_dict = citation_map.sources
                    elif isinstance(citation_map, dict) and "sources" in citation_map:
                        sources_dict = citation_map["sources"]
                    else:
                        sources_dict = {}

                    sources = []
                    for url, src in sources_dict.items():
                        if isinstance(src, dict):
                            sources.append({
                                "index": src.get("citation_index", 0),
                                "title": src.get("title", ""),
                                "url": src.get("url", url),
                                "domain": src.get("domain", ""),
                                "favicon_url": src.get("favicon_url"),
                            })
                        else:
                            sources.append({
                                "index": src.citation_index,
                                "title": src.title,
                                "url": src.url,
                                "domain": src.domain,
                                "favicon_url": src.favicon_url,
                            })
                    if sources:
                        yield {
                            "event": SSEEventType.SOURCES.value,
                            "data": json.dumps({"sources": sorted(sources, key=lambda s: s["index"])})
                        }
                
                # Send final answer
                answer = final_state.get("answer_with_citations") or final_state.get("final_answer", "")
                timing = final_state.get("timing", {})
                
                yield {
                    "event": SSEEventType.COMPLETE.value,
                    "data": json.dumps({
                        "session_id": session_id,
                        "answer": answer,
                        "word_count": len(answer.split()),
                        "total_time_ms": int(sum(timing.values()) * 1000)
                    })
                }
                
            except Exception as e:
                logger.exception(f"Streaming error: {e}")
                yield {
                    "event": SSEEventType.ERROR.value,
                    "data": json.dumps({
                        "message": str(e),
                        "recoverable": False
                    })
                }
    
    return EventSourceResponse(event_generator())


@router.get("/{session_id}", response_model=ResearchResponse)
async def get_research(session_id: str):
    """
    Get research results by session ID.
    """
    store = _get_session_store()
    session_data = await store.get(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return _build_response(
        session_id,
        session_data["state"],
        session_data["query"]
    )


@router.get("/", response_model=SessionListResponse)
async def list_sessions(limit: int = 20, offset: int = 0):
    """
    List recent research sessions.
    """
    store = _get_session_store()
    rows = await store.list_sessions(limit=limit, offset=offset)

    all_sessions = []
    for data in rows:
        state = data.get("state", {})
        answer = state.get("final_answer", "")
        all_sessions.append(SessionInfo(
            session_id=data["session_id"],
            query=data.get("query", ""),
            status=_phase_to_status(state.get("phase", AgentPhase.COMPLETE)),
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
            has_answer=data.get("has_answer", bool(answer)),
        ))

    # Total count for pagination (list_sessions is already sorted by created_at DESC)
    stats = await store.get_stats()
    return SessionListResponse(
        sessions=all_sessions,
        total=stats.get("total_sessions", len(all_sessions))
    )


@router.post("/{session_id}/followup", response_model=ResearchResponse)
async def create_followup(session_id: str, request: FollowUpRequest):
    """
    Ask a follow-up question in an existing session.
    """
    store = _get_session_store()
    session_data = await store.get(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # For follow-up, we include context from previous research
    original_query = session_data.get("query", "")
    previous_answer = session_data.get("state", {}).get("final_answer", "")
    
    # Create enhanced query with context
    enhanced_query = f"""Previous question: {original_query}
Previous answer summary: {previous_answer[:500]}...

Follow-up question: {request.query}"""
    
    new_session_id = str(uuid.uuid4())
    
    try:
        state = await _run_research(
            session_id=new_session_id,
            query=enhanced_query,
            max_iterations=2  # Fewer iterations for follow-ups
        )
        
        return _build_response(new_session_id, state, request.query)
        
    except Exception as e:
        logger.error(f"Follow-up failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a research session.
    """
    store = _get_session_store()
    if not await store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    await store.delete(session_id)
    
    return {"status": "deleted", "session_id": session_id}


# =============================================================================
# QUICK ACTIONS / TRANSFORM ENDPOINTS
# =============================================================================

@router.post("/{session_id}/transform")
async def transform_research(session_id: str, request: "TransformRequest"):
    """
    Apply a quick action transformation to research results.
    
    Available actions:
    - summarize: Condense to key points
    - explain: Simplify explanation (ELI5)
    - compare: Create comparison table
    - timeline: Extract chronological events
    - pros_cons: Analyze advantages/disadvantages
    - key_points: Extract bullet points
    - code_example: Add practical code examples
    - deep_dive: Expand on a specific section
    """
    from src.api.schemas import TransformRequest, TransformResponse, QuickActionType
    from src.core.agents.transformer import TransformerAgent, QuickAction
    import time
    
    # Get session
    store = _get_session_store()
    session_data = await store.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get the answer content to transform
    state = session_data.get("state", {})
    answer_content = state.get("answer_with_citations") or state.get("final_answer", "")
    
    if not answer_content:
        raise HTTPException(
            status_code=400, 
            detail="No answer content available to transform. Research may still be in progress."
        )
    
    # Map API action to agent action
    try:
        agent_action = QuickAction(request.action.value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {request.action}. Valid actions: {[a.value for a in QuickActionType]}"
        )
    
    start_time = time.time()
    
    try:
        # Create transformer agent and perform transformation
        transformer = TransformerAgent()
        result = await transformer.transform(
            action=agent_action,
            content=answer_content,
            target_text=request.target_text,
            context=request.context or "",
            language=request.language
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return TransformResponse(
            session_id=session_id,
            action=request.action,
            original_length=result.original_length,
            transformed_content=result.transformed_content,
            transformed_length=result.transformed_length,
            duration_ms=duration_ms,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Transform failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transformation failed: {str(e)}")


# =============================================================================
# CONVERSATION THREADING ENDPOINTS
# =============================================================================

@router.get("/{session_id}/tree")
async def get_conversation_tree(session_id: str):
    """
    Get the full conversation tree for a session.
    
    Returns all nodes in the conversation with their relationships.
    """
    from src.api.schemas import (
        ConversationTreeResponse,
        ConversationTreeInfoResponse,
        ConversationNodeResponse
    )
    from src.storage import get_conversation_tree
    
    tree = get_conversation_tree()
    nodes = await tree.get_tree(session_id)
    
    if not nodes:
        raise HTTPException(status_code=404, detail="No conversation found for this session")
    
    info = await tree.get_tree_info(session_id)
    
    return ConversationTreeResponse(
        session_id=session_id,
        info=ConversationTreeInfoResponse(**info.to_dict()) if info else None,
        nodes=[ConversationNodeResponse(**node.to_dict()) for node in nodes]
    )


@router.get("/{session_id}/tree/{node_id}/context")
async def get_context_chain(session_id: str, node_id: str, max_depth: int = 5):
    """
    Get the conversation context chain leading to a specific node.
    
    Returns the path from the root to the specified node,
    useful for follow-up questions.
    """
    from src.api.schemas import ContextChainResponse, ConversationNodeResponse
    from src.storage import get_conversation_tree
    
    tree = get_conversation_tree()
    
    # Verify node exists and belongs to session
    node = await tree.get_node(node_id)
    if not node or node.session_id != session_id:
        raise HTTPException(status_code=404, detail="Node not found in this session")
    
    chain = await tree.get_context_chain(node_id, max_depth)
    formatted = await tree.get_formatted_context(node_id, max_depth)
    
    return ContextChainResponse(
        node_id=node_id,
        chain=[ConversationNodeResponse(**n.to_dict()) for n in chain],
        formatted_context=formatted
    )


@router.post("/{session_id}/branch")
async def create_branch(session_id: str, request: "BranchRequest"):
    """
    Create a new branch from an existing conversation node.
    
    This allows exploring alternative research paths from any point
    in the conversation history.
    """
    from src.api.schemas import BranchRequest, ConversationNodeResponse
    from src.storage import get_conversation_tree
    
    tree = get_conversation_tree()
    
    # Verify the node exists and belongs to this session
    parent_node = await tree.get_node(request.node_id)
    if not parent_node:
        raise HTTPException(status_code=404, detail="Node not found")
    if parent_node.session_id != session_id:
        raise HTTPException(status_code=400, detail="Node does not belong to this session")
    
    # Get conversation context for the branch
    context = await tree.get_formatted_context(request.node_id, max_depth=3)
    
    # Run research with context
    new_session_id = str(uuid.uuid4())
    enhanced_query = f"{context}\n\nNew question: {request.query}" if context else request.query
    
    try:
        state = await _run_research(
            session_id=new_session_id,
            query=enhanced_query,
            mode=request.mode,
            max_iterations=2  # Fewer iterations for branches
        )
        
        # Extract response
        answer = state.get("answer_with_citations") or state.get("final_answer", "")
        sources = []
        citation_map = state.get("citation_map")
        if citation_map and hasattr(citation_map, "sources"):
            sources = list(citation_map.sources.keys())
        
        # Create branch node
        branch_node = await tree.branch_from(
            node_id=request.node_id,
            new_query=request.query,
            new_response=answer,
            sources=sources,
            metadata={"mode": request.mode, "branch_session_id": new_session_id}
        )
        
        if not branch_node:
            raise HTTPException(status_code=500, detail="Failed to create branch")
        
        # Also return the full research response
        response = _build_response(new_session_id, state, request.query)
        
        return {
            "branch_node": ConversationNodeResponse(**branch_node.to_dict()),
            "research": response
        }
        
    except Exception as e:
        logger.error(f"Branch creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Branch creation failed: {str(e)}")


@router.delete("/{session_id}/tree/{node_id}")
async def delete_conversation_node(session_id: str, node_id: str, recursive: bool = True):
    """
    Delete a conversation node and optionally its descendants.
    
    Args:
        session_id: Session ID
        node_id: Node ID to delete
        recursive: If True, delete all descendant nodes too
    """
    from src.storage import get_conversation_tree
    
    tree = get_conversation_tree()
    
    # Verify node belongs to session
    node = await tree.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.session_id != session_id:
        raise HTTPException(status_code=400, detail="Node does not belong to this session")
    
    deleted_count = await tree.delete_node(node_id, recursive=recursive)
    
    return {
        "status": "deleted",
        "node_id": node_id,
        "deleted_count": deleted_count
    }


@router.get("/{session_id}/tree/export")
async def export_conversation(session_id: str):
    """
    Export the full conversation tree for saving/sharing.
    
    Returns a complete export with all nodes and metadata.
    """
    from src.storage import get_conversation_tree
    
    tree = get_conversation_tree()
    
    export_data = await tree.export_tree(session_id)
    
    if not export_data.get("nodes"):
        raise HTTPException(status_code=404, detail="No conversation found for this session")
    
    return export_data
