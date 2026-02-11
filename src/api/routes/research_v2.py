"""
Research API Routes v2.0.

Multi-agent research endpoints with advanced verification and streaming.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from src.config import get_settings
from src.utils.logging import get_logger
from src.utils.exceptions import DiogenesError
from src.api.schemas import (
    ResearchRequest,
    ResearchResponse,
    ResearchAnswer,
    ResearchTiming,
    Source,
    ResearchStatus,
    SSEEventType,
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


logger = get_logger(__name__)
router = APIRouter(prefix="/v2/research", tags=["research-v2"])

# Research concurrency gate (shared with V1 via same config)
_research_semaphore: asyncio.Semaphore | None = None


def _get_research_semaphore() -> asyncio.Semaphore:
    """Get or create the research concurrency semaphore."""
    global _research_semaphore
    if _research_semaphore is None:
        settings = get_settings()
        _research_semaphore = asyncio.Semaphore(settings.api.max_concurrent_research)
    return _research_semaphore


def _get_orchestrator(mode: SearchMode) -> ResearchOrchestrator:
    """Create a new orchestrator for each request to avoid shared mutable state."""
    return ResearchOrchestrator(mode=mode)


def _phase_to_status(phase: ResearchPhase) -> ResearchStatus:
    """Convert research phase to API status."""
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


@router.post("/", response_model=ResearchResponse)
async def create_research_v2(
    request: ResearchRequest,
    profile: str = Query(default="auto", description="Research profile (auto, general, academic, technical, etc.)")
):
    """
    Start a new research query using the multi-agent system.
    
    The v2 API provides:
    - Multi-agent research with specialized agents
    - Automatic claim verification
    - Reliability scoring
    - Profile-based optimization
    
    Args:
        request: Research request with query and mode
        profile: Research profile to use (or "auto" for detection)
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    logger.info(f"[v2] Starting research: {request.query[:50]}... (session: {session_id})")
    
    async with _get_research_semaphore():
        try:
            # Detect or use specified profile
            if profile == "auto":
                profile_type = detect_profile(request.query)
            else:
                try:
                    profile_type = ProfileType(profile)
                except ValueError:
                    profile_type = ProfileType.GENERAL
            
            research_profile = get_profile(profile_type)
            logger.info(f"Using profile: {profile_type.value}")
            
            # Get mode from request or profile
            mode_str = request.mode.upper()
            try:
                mode = SearchMode[mode_str]
            except KeyError:
                mode = research_profile.default_mode
            
            # Get orchestrator and run research
            orchestrator = _get_orchestrator(mode)
            
            result = await orchestrator.research(
                query=request.query,
                style=research_profile.output.default_style,
            )
            
            # Build response
            timing = ResearchTiming(
                total_ms=int(result.duration_seconds * 1000)
            )
            
            answer = ResearchAnswer(
                content=result.answer,
                word_count=len(result.answer.split()),
                has_citations="[" in result.answer and "]" in result.answer
            ) if result.answer else None
            
            # Convert sources
            sources = []
            for i, src in enumerate(result.sources, 1):
                sources.append(Source(
                    index=i,
                    title=src.get("title", "Untitled"),
                    url=src.get("url", ""),
                    domain=src.get("domain", ""),
                    quality_score=src.get("quality_score") or 0.0
                ))
            
            return ResearchResponse(
                session_id=session_id,
                query=request.query,
                status=ResearchStatus.COMPLETE,
                answer=answer,
                sources=sources,
                timing=timing,
                errors=[],
                created_at=datetime.utcnow(),
                metadata={
                    "profile": profile_type.value,
                    "mode": mode.value,
                    "reliability_score": result.reliability_score,
                    "confidence": result.confidence,
                    "iterations": result.iterations,
                    "verified_claims_count": len(result.verified_claims),
                    "contradictions_count": len(result.contradictions),
                }
            )
            
        except DiogenesError as e:
            logger.error(f"Research failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Research failed unexpectedly")


@router.post("/stream")
async def stream_research_v2(
    request: ResearchRequest,
    profile: str = Query(default="auto", description="Research profile")
):
    """
    Start research with SSE streaming using multi-agent system.
    
    Returns an event stream with progress updates including:
    - Phase transitions
    - Source discovery
    - Verification progress
    - Answer chunks (for typing effect)
    """
    session_id = str(uuid.uuid4())
    
    logger.info(f"[v2] Starting streaming research: {request.query[:50]}... (session: {session_id})")
    
    async def event_generator() -> AsyncGenerator[dict, None]:
        async with _get_research_semaphore():
            try:
                # Send initial status
                yield {
                    "event": SSEEventType.STATUS.value,
                    "data": json.dumps({
                        "session_id": session_id,
                        "phase": "initializing",
                        "message": "Multi-agent research starting..."
                    })
                }
                
                # Detect profile
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
                        "description": research_profile.description
                    })
                }
                
                # Get mode
                mode_str = request.mode.upper()
                try:
                    mode = SearchMode[mode_str]
                except KeyError:
                    mode = research_profile.default_mode
                
                # Get orchestrator
                orchestrator = _get_orchestrator(mode)
                
                # Stream research
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
                                "message": event_data.get("messages", ["Processing..."])[-1] if event_data.get("messages") else "Processing..."
                            })
                        }
                    
                    elif event_type == "source":
                        yield {
                            "event": SSEEventType.SOURCES.value,
                            "data": json.dumps({
                                "url": event_data.get("url", ""),
                                "title": event_data.get("title", "")
                            })
                        }
                    
                    elif event_type == "answer_chunk":
                        yield {
                            "event": SSEEventType.SYNTHESIS.value,
                            "data": json.dumps({
                                "content": event_data.get("content", "")
                            })
                        }
                    
                    elif event_type == "complete":
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
                                    "iterations": event_data.get("iterations", 1)
                                }
                            })
                        }
                    
                    elif event_type == "error":
                        yield {
                            "event": SSEEventType.ERROR.value,
                            "data": json.dumps({
                                "session_id": session_id,
                                "error": event_data.get("error", "Unknown error")
                            })
                        }
                
            except Exception as e:
                logger.exception(f"Streaming error: {e}")
                yield {
                    "event": SSEEventType.ERROR.value,
                    "data": json.dumps({
                        "session_id": session_id,
                        "error": str(e)
                    })
                }
    
    return EventSourceResponse(event_generator())


@router.get("/profiles")
async def list_profiles():
    """
    List available research profiles.
    
    Returns all available profiles with their configurations.
    """
    from src.core.agents.profiles import PROFILES
    
    profiles = []
    for profile_type, profile in PROFILES.items():
        profiles.append({
            "id": profile_type.value,
            "name": profile.name,
            "description": profile.description,
            "default_mode": profile.default_mode.value,
            "output_style": profile.output.default_style,
            "verification": {
                "min_confidence": profile.verification.min_confidence,
                "strict_mode": profile.verification.strict_mode,
            }
        })
    
    return {"profiles": profiles}


@router.get("/health")
async def health_check():
    """
    Health check for v2 research API.
    
    Returns status of all agent components.
    """
    status = {
        "status": "healthy",
        "version": "2.0",
        "agents": {
            "coordinator": "available",
            "researcher": "available",
            "verifier": "available",
            "writer": "available",
        }
    }
    
    # Check if any orchestrators are initialized
    if _orchestrators:
        for mode, orch in _orchestrators.items():
            metrics = orch.get_agent_metrics()
            status["orchestrators"] = {mode: "active"}
    
    return status
