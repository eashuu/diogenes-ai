"""
Unified Research API Routes.

Multi-agent research with session persistence, streaming, follow-ups,
quick-action transforms, and conversation tree management — exposed
as the ``/api/v1/research`` endpoint family.

This module supersedes the former split V1 (LangGraph) and V2 (multi-agent)
routers.  The multi-agent orchestrator (``ResearchOrchestrator``) from V2 is
the sole research engine; all session data is persisted via
``SQLiteSessionStore``; and the convenience endpoints (follow-up, transform,
conversation tree, branch) from the original V1 router are preserved.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from src.config import get_settings
from src.utils.logging import get_logger
from src.utils.exceptions import DiogenesError
from src.api.schemas import (
    ResearchRequest,
    FollowUpRequest,
    ResearchResponse,
    ResearchAnswer,
    ResearchTiming,
    Source,
    ResearchStatus,
    SSEEventType,
    SessionInfo,
    SessionListResponse,
)
from src.core.agents import (
    ResearchOrchestrator,
    ResearchPhase,
    create_orchestrator,
)
from src.core.agents.profiles import (
    ProfileType,
    get_profile,
    detect_profile,
)
from src.core.agent.modes import SearchMode
from src.storage import SQLiteSessionStore


logger = get_logger(__name__)
router = APIRouter(prefix="/research", tags=["research"])

# ---------------------------------------------------------------------------
# Singletons / lazy helpers
# ---------------------------------------------------------------------------

_research_semaphore: asyncio.Semaphore | None = None
_session_store: SQLiteSessionStore | None = None


def _get_research_semaphore() -> asyncio.Semaphore:
    """Get or create the research concurrency semaphore."""
    global _research_semaphore
    if _research_semaphore is None:
        settings = get_settings()
        _research_semaphore = asyncio.Semaphore(settings.api.max_concurrent_research)
    return _research_semaphore


def _get_session_store() -> SQLiteSessionStore:
    """Get or lazily initialise the session store."""
    global _session_store
    if _session_store is None:
        settings = get_settings()
        _session_store = SQLiteSessionStore(settings.session.database)
    return _session_store


def _get_orchestrator(mode: SearchMode) -> ResearchOrchestrator:
    """Create a fresh orchestrator per request (no shared state)."""
    return ResearchOrchestrator(mode=mode)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _phase_to_status(phase: ResearchPhase) -> ResearchStatus:
    """Convert ``ResearchPhase`` enum to ``ResearchStatus``."""
    mapping = {
        ResearchPhase.INITIALIZING: ResearchStatus.PENDING,
        ResearchPhase.PLANNING: ResearchStatus.PLANNING,
        ResearchPhase.RESEARCHING: ResearchStatus.SEARCHING,
        ResearchPhase.PROCESSING: ResearchStatus.PROCESSING,
        ResearchPhase.VERIFYING: ResearchStatus.REFLECTING,
        ResearchPhase.SYNTHESIZING: ResearchStatus.SYNTHESIZING,
        ResearchPhase.REVIEWING: ResearchStatus.REFLECTING,
        ResearchPhase.COMPLETE: ResearchStatus.COMPLETE,
        ResearchPhase.FAILED: ResearchStatus.ERROR,
    }
    return mapping.get(phase, ResearchStatus.PENDING)


def _build_response(
    session_id: str,
    result,
    query: str,
    *,
    profile_type: ProfileType | None = None,
    mode: SearchMode | None = None,
) -> ResearchResponse:
    """Build a ``ResearchResponse`` from an orchestrator ``ResearchResult``."""
    timing = ResearchTiming(
        total_ms=int(result.duration_seconds * 1000),
    )

    answer = ResearchAnswer(
        content=result.answer,
        word_count=len(result.answer.split()),
        has_citations="[" in result.answer and "]" in result.answer,
    ) if result.answer else None

    sources = []
    for i, src in enumerate(result.sources, 1):
        sources.append(Source(
            index=i,
            title=src.get("title", "Untitled"),
            url=src.get("url", ""),
            domain=src.get("domain", ""),
            quality_score=src.get("quality_score") or 0.0,
        ))

    metadata: dict = {
        "reliability_score": result.reliability_score,
        "confidence": result.confidence,
        "iterations": result.iterations,
        "verified_claims_count": len(result.verified_claims),
        "contradictions_count": len(result.contradictions),
    }
    if profile_type:
        metadata["profile"] = profile_type.value
    if mode:
        metadata["mode"] = mode.value

    return ResearchResponse(
        session_id=session_id,
        query=query,
        status=ResearchStatus.COMPLETE,
        answer=answer,
        sources=sources,
        timing=timing,
        errors=[],
        created_at=datetime.utcnow(),
        metadata=metadata,
    )


async def _persist_session(session_id: str, query: str, result) -> None:
    """Store research results in SQLite for later retrieval."""
    store = _get_session_store()
    sources_list = []
    for s in result.sources:
        sources_list.append({
            "title": s.get("title", ""),
            "url": s.get("url", ""),
            "domain": s.get("domain", ""),
            "quality_score": s.get("quality_score", 0.0),
        })
    await store.set(session_id, {
        "query": query,
        "state": {
            "phase": "complete",
            "answer": result.answer,
            "final_answer": result.answer,     # SQLiteSessionStore keys on this for has_answer
            "sources": sources_list,
            "reliability_score": result.reliability_score,
            "confidence": result.confidence,
            "iterations": result.iterations,
            "duration_seconds": result.duration_seconds,
        },
    })


# =========================================================================
# RESEARCH ENDPOINTS
# =========================================================================

@router.post("/", response_model=ResearchResponse)
async def create_research(
    request: ResearchRequest,
    profile: str = Query(default="auto", description="Research profile (auto, general, academic, technical, etc.)"),
):
    """
    Start a new research query (blocking).

    Uses the multi-agent orchestrator with specialised agents for
    planning, searching, crawling, verification, and synthesis.
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()

    logger.info(f"Starting research: {request.query[:50]}... (session: {session_id})")

    async with _get_research_semaphore():
        try:
            # Profile detection
            if profile == "auto":
                profile_type = detect_profile(request.query)
            else:
                try:
                    profile_type = ProfileType(profile)
                except ValueError:
                    profile_type = ProfileType.GENERAL

            research_profile = get_profile(profile_type)
            logger.info(f"Using profile: {profile_type.value}")

            # Determine search mode
            mode_str = request.mode.upper()
            try:
                mode = SearchMode[mode_str]
            except KeyError:
                mode = research_profile.default_mode

            # Execute research
            orchestrator = _get_orchestrator(mode)
            result = await orchestrator.research(
                query=request.query,
                style=research_profile.output.default_style,
            )

            # Persist
            await _persist_session(session_id, request.query, result)

            return _build_response(
                session_id, result, request.query,
                profile_type=profile_type, mode=mode,
            )

        except DiogenesError as e:
            logger.error(f"Research failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Research failed unexpectedly")


@router.post("/stream")
async def stream_research(
    request: ResearchRequest,
    profile: str = Query(default="auto", description="Research profile"),
):
    """
    Start research with SSE streaming.

    Returns an event stream with progress updates including phase
    transitions, source discovery, verification progress, and answer
    chunks (for a typing effect).
    """
    session_id = str(uuid.uuid4())

    logger.info(f"Starting streaming research: {request.query[:50]}... (session: {session_id})")

    async def event_generator() -> AsyncGenerator[dict, None]:
        async with _get_research_semaphore():
            try:
                yield {
                    "event": SSEEventType.STATUS.value,
                    "data": json.dumps({
                        "session_id": session_id,
                        "phase": "initializing",
                        "message": "Multi-agent research starting...",
                    }),
                }

                # Profile
                if profile == "auto":
                    profile_type = detect_profile(request.query)
                else:
                    try:
                        profile_type = ProfileType(profile)
                    except ValueError:
                        profile_type = ProfileType.GENERAL

                research_profile = get_profile(profile_type)

                yield {
                    "event": "profile",
                    "data": json.dumps({
                        "profile": profile_type.value,
                        "name": research_profile.name,
                        "description": research_profile.description,
                    }),
                }

                # Mode
                mode_str = request.mode.upper()
                try:
                    mode = SearchMode[mode_str]
                except KeyError:
                    mode = research_profile.default_mode

                orchestrator = _get_orchestrator(mode)

                async for event in orchestrator.research_stream(
                    query=request.query,
                    style=research_profile.output.default_style,
                ):
                    event_type = event.get("type", "progress")
                    event_data = event.get("data", {})

                    if event_type == "progress":
                        yield {
                            "event": SSEEventType.STATUS.value,
                            "data": json.dumps({
                                "session_id": session_id,
                                "phase": event_data.get("phase", "processing"),
                                "progress": event_data.get("progress_pct", 0),
                                "sources_found": event_data.get("sources_found", 0),
                                "message": (event_data.get("messages", ["Processing..."])[-1]
                                            if event_data.get("messages") else "Processing..."),
                            }),
                        }

                    elif event_type == "source":
                        yield {
                            "event": SSEEventType.SOURCES.value,
                            "data": json.dumps({
                                "url": event_data.get("url", ""),
                                "title": event_data.get("title", ""),
                            }),
                        }

                    elif event_type == "answer_chunk":
                        yield {
                            "event": SSEEventType.SYNTHESIS.value,
                            "data": json.dumps({
                                "content": event_data.get("content", ""),
                            }),
                        }

                    elif event_type == "complete":
                        # Persist session on completion
                        class _R:
                            """Lightweight result shim for _persist_session."""
                            answer = event_data.get("answer", "")
                            sources = event_data.get("sources", [])
                            reliability_score = event_data.get("reliability_score", 0)
                            confidence = event_data.get("confidence", 0)
                            iterations = event_data.get("iterations", 1)
                            duration_seconds = event_data.get("duration_seconds", 0)
                            verified_claims: list = []
                            contradictions: list = []

                        await _persist_session(session_id, request.query, _R())

                        yield {
                            "event": SSEEventType.COMPLETE.value,
                            "data": json.dumps({
                                "session_id": session_id,
                                "answer": event_data.get("answer", ""),
                                "sources_count": len(event_data.get("sources", [])),
                                "reliability_score": event_data.get("reliability_score", 0),
                                "confidence": event_data.get("confidence", 0),
                                "duration_seconds": event_data.get("duration_seconds", 0),
                                "metadata": {
                                    "profile": profile_type.value,
                                    "mode": mode.value,
                                    "iterations": event_data.get("iterations", 1),
                                },
                            }),
                        }

                    elif event_type == "error":
                        yield {
                            "event": SSEEventType.ERROR.value,
                            "data": json.dumps({
                                "session_id": session_id,
                                "error": event_data.get("error", "Unknown error"),
                            }),
                        }

            except Exception as e:
                logger.exception(f"Streaming error: {e}")
                yield {
                    "event": SSEEventType.ERROR.value,
                    "data": json.dumps({
                        "session_id": session_id,
                        "error": str(e),
                    }),
                }

    return EventSourceResponse(event_generator())


# =========================================================================
# SESSION MANAGEMENT
# =========================================================================

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(limit: int = 20, offset: int = 0):
    """List recent research sessions."""
    store = _get_session_store()
    rows = await store.list_sessions(limit=limit, offset=offset)

    all_sessions = []
    for data in rows:
        state = data.get("state", {})
        answer = state.get("answer", "")
        all_sessions.append(SessionInfo(
            session_id=data["session_id"],
            query=data.get("query", ""),
            status=ResearchStatus.COMPLETE if state.get("phase") == "complete" else ResearchStatus.ERROR,
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
            has_answer=bool(answer),
        ))

    stats = await store.get_stats()
    return SessionListResponse(
        sessions=all_sessions,
        total=stats.get("total_sessions", len(all_sessions)),
    )


@router.get("/{session_id}", response_model=ResearchResponse)
async def get_research(session_id: str):
    """Get research results by session ID."""
    store = _get_session_store()
    session_data = await store.get(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session_data.get("state", {})
    query = session_data.get("query", "")

    answer_content = state.get("answer", "")
    answer = ResearchAnswer(
        content=answer_content,
        word_count=len(answer_content.split()),
        has_citations="[" in answer_content and "]" in answer_content,
    ) if answer_content else None

    sources = []
    for i, src in enumerate(state.get("sources", []), 1):
        sources.append(Source(
            index=i,
            title=src.get("title", "Untitled"),
            url=src.get("url", ""),
            domain=src.get("domain", ""),
            quality_score=src.get("quality_score", 0.0),
        ))

    timing = ResearchTiming(
        total_ms=int(state.get("duration_seconds", 0) * 1000),
    )

    return ResearchResponse(
        session_id=session_id,
        query=query,
        status=ResearchStatus.COMPLETE if state.get("phase") == "complete" else ResearchStatus.ERROR,
        answer=answer,
        sources=sources,
        timing=timing,
        errors=[],
        created_at=datetime.utcnow(),
        metadata={
            "reliability_score": state.get("reliability_score", 0),
            "confidence": state.get("confidence", 0),
            "iterations": state.get("iterations", 1),
        },
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a research session."""
    store = _get_session_store()
    if not await store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    await store.delete(session_id)
    return {"status": "deleted", "session_id": session_id}


# =========================================================================
# FOLLOW-UP
# =========================================================================

@router.post("/{session_id}/followup", response_model=ResearchResponse)
async def create_followup(session_id: str, request: FollowUpRequest):
    """Ask a follow-up question in an existing session."""
    store = _get_session_store()
    session_data = await store.get(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session_data.get("state", {})
    original_query = session_data.get("query", "")
    previous_answer = state.get("answer", "")

    enhanced_query = (
        f"Previous question: {original_query}\n"
        f"Previous answer summary: {previous_answer[:500]}...\n\n"
        f"Follow-up question: {request.query}"
    )

    new_session_id = str(uuid.uuid4())

    async with _get_research_semaphore():
        try:
            orchestrator = _get_orchestrator(SearchMode.BALANCED)
            result = await orchestrator.research(
                query=enhanced_query,
                style="comprehensive",
            )
            await _persist_session(new_session_id, request.query, result)
            return _build_response(new_session_id, result, request.query)
        except Exception as e:
            logger.error(f"Follow-up failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# PROFILES & HEALTH
# =========================================================================

@router.get("/profiles")
async def list_profiles():
    """List available research profiles with their configurations."""
    from src.core.agents.profiles import PROFILES

    profiles = []
    for profile_type, p in PROFILES.items():
        profiles.append({
            "id": profile_type.value,
            "name": p.name,
            "description": p.description,
            "default_mode": p.default_mode.value,
            "output_style": p.output.default_style,
            "verification": {
                "min_confidence": p.verification.min_confidence,
                "strict_mode": p.verification.strict_mode,
            },
        })
    return {"profiles": profiles}


@router.get("/health")
async def health_check():
    """Health check for the research API."""
    return {
        "status": "healthy",
        "version": "1.0",
        "agents": {
            "coordinator": "available",
            "researcher": "available",
            "verifier": "available",
            "writer": "available",
        },
    }


# =========================================================================
# QUICK-ACTION TRANSFORMS
# =========================================================================

@router.post("/{session_id}/transform")
async def transform_research(session_id: str, request: "TransformRequest"):
    """
    Apply a quick-action transformation to research results.

    Available actions: summarize, explain, compare, timeline,
    pros_cons, key_points, code_example, deep_dive.
    """
    from src.api.schemas import TransformRequest, TransformResponse, QuickActionType
    from src.core.agents.transformer import TransformerAgent, QuickAction

    store = _get_session_store()
    session_data = await store.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session_data.get("state", {})
    answer_content = state.get("answer", "")

    if not answer_content:
        raise HTTPException(
            status_code=400,
            detail="No answer content available to transform.",
        )

    try:
        agent_action = QuickAction(request.action.value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {request.action}. Valid: {[a.value for a in QuickActionType]}",
        )

    start_time = time.time()
    try:
        transformer = TransformerAgent()
        result = await transformer.transform(
            action=agent_action,
            content=answer_content,
            target_text=request.target_text,
            context=request.context or "",
            language=request.language,
        )
        duration_ms = int((time.time() - start_time) * 1000)

        return TransformResponse(
            session_id=session_id,
            action=request.action,
            original_length=result.original_length,
            transformed_content=result.transformed_content,
            transformed_length=result.transformed_length,
            duration_ms=duration_ms,
            metadata=result.metadata,
        )
    except Exception as e:
        logger.error(f"Transform failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transformation failed: {str(e)}")


# =========================================================================
# CONVERSATION TREE
# =========================================================================

@router.get("/{session_id}/tree")
async def get_conversation_tree(session_id: str):
    """Get the full conversation tree for a session."""
    from src.api.schemas import (
        ConversationTreeResponse,
        ConversationTreeInfoResponse,
        ConversationNodeResponse,
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
        nodes=[ConversationNodeResponse(**node.to_dict()) for node in nodes],
    )


@router.get("/{session_id}/tree/{node_id}/context")
async def get_context_chain(session_id: str, node_id: str, max_depth: int = 5):
    """Get the conversation context chain leading to a specific node."""
    from src.api.schemas import ContextChainResponse, ConversationNodeResponse
    from src.storage import get_conversation_tree

    tree = get_conversation_tree()
    node = await tree.get_node(node_id)
    if not node or node.session_id != session_id:
        raise HTTPException(status_code=404, detail="Node not found in this session")

    chain = await tree.get_context_chain(node_id, max_depth)
    formatted = await tree.get_formatted_context(node_id, max_depth)

    return ContextChainResponse(
        node_id=node_id,
        chain=[ConversationNodeResponse(**n.to_dict()) for n in chain],
        formatted_context=formatted,
    )


@router.post("/{session_id}/branch")
async def create_branch(session_id: str, request: "BranchRequest"):
    """Create a new branch from an existing conversation node."""
    from src.api.schemas import BranchRequest, ConversationNodeResponse
    from src.storage import get_conversation_tree

    tree = get_conversation_tree()

    parent_node = await tree.get_node(request.node_id)
    if not parent_node:
        raise HTTPException(status_code=404, detail="Node not found")
    if parent_node.session_id != session_id:
        raise HTTPException(status_code=400, detail="Node does not belong to this session")

    context = await tree.get_formatted_context(request.node_id, max_depth=3)
    enhanced_query = f"{context}\n\nNew question: {request.query}" if context else request.query

    new_session_id = str(uuid.uuid4())

    async with _get_research_semaphore():
        try:
            mode_str = (request.mode or "balanced").upper()
            try:
                mode = SearchMode[mode_str]
            except KeyError:
                mode = SearchMode.BALANCED

            orchestrator = _get_orchestrator(mode)
            result = await orchestrator.research(
                query=enhanced_query,
                style="comprehensive",
            )
            await _persist_session(new_session_id, request.query, result)

            branch_node = await tree.branch_from(
                node_id=request.node_id,
                new_query=request.query,
                new_response=result.answer,
                sources=[s.get("url", "") for s in result.sources],
                metadata={"mode": mode.value, "branch_session_id": new_session_id},
            )

            if not branch_node:
                raise HTTPException(status_code=500, detail="Failed to create branch")

            return {
                "branch_node": ConversationNodeResponse(**branch_node.to_dict()),
                "research": _build_response(new_session_id, result, request.query, mode=mode),
            }
        except Exception as e:
            logger.error(f"Branch creation failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Branch creation failed: {str(e)}")


@router.delete("/{session_id}/tree/{node_id}")
async def delete_conversation_node(session_id: str, node_id: str, recursive: bool = True):
    """Delete a conversation node and optionally its descendants."""
    from src.storage import get_conversation_tree

    tree = get_conversation_tree()
    node = await tree.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.session_id != session_id:
        raise HTTPException(status_code=400, detail="Node does not belong to this session")

    deleted_count = await tree.delete_node(node_id, recursive=recursive)
    return {"status": "deleted", "node_id": node_id, "deleted_count": deleted_count}


@router.get("/{session_id}/tree/export")
async def export_conversation(session_id: str):
    """Export the full conversation tree for saving / sharing."""
    from src.storage import get_conversation_tree

    tree = get_conversation_tree()
    export_data = await tree.export_tree(session_id)

    if not export_data.get("nodes"):
        raise HTTPException(status_code=404, detail="No conversation found for this session")

    return export_data
