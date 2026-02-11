"""
API Request/Response Schemas.

Pydantic models for API validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, HttpUrl, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class ResearchStatus(str, Enum):
    """Status of a research request."""
    PENDING = "pending"
    PLANNING = "planning"
    SEARCHING = "searching"
    CRAWLING = "crawling"
    PROCESSING = "processing"
    REFLECTING = "reflecting"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    ERROR = "error"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class ResearchRequest(BaseModel):
    """Request to start a research query."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The research question to answer"
    )
    mode: str = Field(
        default="balanced",
        pattern="^(quick|balanced|full|research|deep)$",
        description="Research mode: quick (~30s, 3 sources), balanced (~2min, 15 sources), full (~5min, 25 sources), research (~10min, 40 sources), deep (~20min, 60 sources)"
    )
    max_iterations: int = Field(
        default=None,
        ge=1,
        le=10,
        description="Maximum reflection iterations (overrides mode default)"
    )
    streaming: bool = Field(
        default=True,
        description="Whether to stream results via SSE"
    )
    
    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize query input to prevent issues."""
        # Strip whitespace
        v = v.strip()
        
        # Remove null bytes and control characters
        v = ''.join(char for char in v if ord(char) >= 32 or char in '\n\r\t')
        
        # Collapse multiple whitespace
        import re
        v = re.sub(r'\s+', ' ', v)
        
        if len(v) < 3:
            raise ValueError('Query must be at least 3 characters after sanitization')
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What are the latest developments in quantum computing?",
                    "mode": "balanced",
                    "max_iterations": None,
                    "streaming": True
                },
                {
                    "query": "What is Python?",
                    "mode": "quick",
                    "streaming": False
                },
                {
                    "query": "Explain quantum entanglement in detail",
                    "mode": "research",
                    "max_iterations": 7,
                    "streaming": True
                }
            ]
        }
    }


class FollowUpRequest(BaseModel):
    """Request for a follow-up question."""
    session_id: str = Field(
        ...,
        description="Session ID from the original research"
    )
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The follow-up question"
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class SourceQualityBadges(BaseModel):
    """Visual quality indicators for a source."""
    is_verified: bool = Field(
        default=False,
        description="Cross-referenced with other sources"
    )
    is_recent: bool = Field(
        default=False,
        description="Published within relevant timeframe"
    )
    is_authoritative: bool = Field(
        default=False,
        description="High domain authority (>0.8)"
    )
    is_primary_source: bool = Field(
        default=False,
        description="Original research or primary data"
    )
    is_academic: bool = Field(
        default=False,
        description="From academic/research institution"
    )


class SourceScoreBreakdown(BaseModel):
    """Breakdown of quality score components."""
    authority: float = Field(default=0.0, ge=0.0, le=1.0, description="Domain authority score")
    freshness: float = Field(default=0.0, ge=0.0, le=1.0, description="Content freshness score")
    relevance: float = Field(default=0.0, ge=0.0, le=1.0, description="Query relevance score")
    content_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Content quality score")


class Source(BaseModel):
    """A source used in the research."""
    index: int = Field(..., description="Citation index [1], [2], etc.")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    domain: str = Field(..., description="Source domain")
    favicon_url: str | None = Field(None, description="Favicon URL")
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall quality score 0-1"
    )
    badges: SourceQualityBadges | None = Field(
        default=None,
        description="Visual quality indicators"
    )
    score_breakdown: SourceScoreBreakdown | None = Field(
        default=None,
        description="Breakdown of quality score components"
    )
    verification_status: str = Field(
        default="unverified",
        description="Verification status: verified, unverified, disputed"
    )
    published_date: str | None = Field(
        default=None,
        description="Publication date if known"
    )


class ResearchAnswer(BaseModel):
    """The research answer with citations."""
    content: str = Field(..., description="Answer content with [n] citations")
    word_count: int = Field(..., description="Word count")
    has_citations: bool = Field(..., description="Whether answer has citations")


class ResearchTiming(BaseModel):
    """Timing breakdown for the research."""
    planning_ms: int | None = Field(None, description="Planning time in ms")
    search_ms: int | None = Field(None, description="Search time in ms")
    crawl_ms: int | None = Field(None, description="Crawl time in ms")
    processing_ms: int | None = Field(None, description="Processing time in ms")
    synthesis_ms: int | None = Field(None, description="Synthesis time in ms")
    total_ms: int = Field(..., description="Total time in ms")


class SuggestionResponse(BaseModel):
    """Suggested follow-up questions and related topics."""
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="Follow-up questions the user might want to ask"
    )
    related_topics: list[str] = Field(
        default_factory=list,
        description="Related topics to explore"
    )


class ResearchResponse(BaseModel):
    """Complete research response."""
    session_id: str = Field(..., description="Unique session identifier")
    query: str = Field(..., description="Original query")
    status: ResearchStatus = Field(..., description="Research status")
    answer: ResearchAnswer | None = Field(None, description="Research answer")
    sources: list[Source] = Field(default_factory=list, description="Sources used")
    suggestions: SuggestionResponse | None = Field(
        None, 
        description="Suggested follow-up questions and related topics"
    )
    timing: ResearchTiming | None = Field(None, description="Timing breakdown")
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Any errors encountered"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the research was created"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (v2: includes profile, reliability_score, confidence)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "abc123",
                    "query": "What are the latest developments in quantum computing?",
                    "status": "complete",
                    "answer": {
                        "content": "Quantum computing has seen significant advances...[1]",
                        "word_count": 250,
                        "has_citations": True
                    },
                    "sources": [
                        {
                            "index": 1,
                            "title": "Quantum Computing News",
                            "url": "https://example.com/quantum",
                            "domain": "example.com",
                            "favicon_url": "https://example.com/favicon.ico",
                            "quality_score": 0.85
                        }
                    ],
                    "timing": {
                        "planning_ms": 500,
                        "search_ms": 1200,
                        "crawl_ms": 3000,
                        "processing_ms": 800,
                        "synthesis_ms": 2000,
                        "total_ms": 7500
                    },
                    "errors": [],
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }


class ResearchStartResponse(BaseModel):
    """Response when research is started (for streaming)."""
    session_id: str = Field(..., description="Session ID to track")
    status: ResearchStatus = Field(
        default=ResearchStatus.PENDING,
        description="Initial status"
    )
    stream_url: str = Field(..., description="SSE stream URL")


# =============================================================================
# SSE EVENT SCHEMAS
# =============================================================================

class SSEEventType(str, Enum):
    """Types of SSE events."""
    STATUS = "status"
    PLANNING = "planning"
    SEARCH = "search"
    CRAWL = "crawl"
    PROCESSING = "processing"
    REFLECTION = "reflection"
    SYNTHESIS = "synthesis"
    ANSWER_CHUNK = "answer_chunk"
    SOURCES = "sources"
    SUGGESTIONS = "suggestions"
    COMPLETE = "complete"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class SSEEvent(BaseModel):
    """An SSE event."""
    event: SSEEventType = Field(..., description="Event type")
    data: dict[str, Any] = Field(..., description="Event data")


class StatusEvent(BaseModel):
    """Status update event data."""
    phase: ResearchStatus
    message: str


class PlanningEvent(BaseModel):
    """Planning complete event data."""
    sub_queries: list[str]
    intent: str


class SearchEvent(BaseModel):
    """Search complete event data."""
    total_results: int
    urls_to_crawl: int


class CrawlEvent(BaseModel):
    """Crawl complete event data."""
    crawled: int
    failed: int


class ProcessingEvent(BaseModel):
    """Processing complete event data."""
    documents: int
    facts: int


class ReflectionEvent(BaseModel):
    """Reflection complete event data."""
    needs_more_research: bool
    completeness: float
    gaps: list[str]


class AnswerChunkEvent(BaseModel):
    """Streaming answer chunk."""
    chunk: str
    is_final: bool = False


class SourcesEvent(BaseModel):
    """Sources event data."""
    sources: list[Source]


class SuggestionsEvent(BaseModel):
    """Suggestions event data - follow-up questions and related topics."""
    suggested_questions: list[str]
    related_topics: list[str]


class CompleteEvent(BaseModel):
    """Research complete event data."""
    answer: ResearchAnswer
    total_time_ms: int


class ErrorEvent(BaseModel):
    """Error event data."""
    message: str
    phase: str | None = None
    recoverable: bool = False


# =============================================================================
# SESSION SCHEMAS
# =============================================================================

class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    query: str
    status: ResearchStatus
    created_at: datetime
    updated_at: datetime
    has_answer: bool


class SessionListResponse(BaseModel):
    """List of sessions."""
    sessions: list[SessionInfo]
    total: int


class SessionDetailResponse(BaseModel):
    """Detailed session information."""
    session: SessionInfo
    research: ResearchResponse | None = None


# =============================================================================
# HEALTH CHECK SCHEMAS
# =============================================================================

class ServiceHealth(BaseModel):
    """Health status of a service."""
    name: str
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Overall health check response."""
    status: str = Field(..., description="overall, healthy, or unhealthy")
    version: str
    services: list[ServiceHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# QUICK ACTIONS / TRANSFORM SCHEMAS
# =============================================================================

class QuickActionType(str, Enum):
    """Available quick action transformations."""
    SUMMARIZE = "summarize"           # Condense to key points
    EXPLAIN_SIMPLE = "explain"        # Simplify explanation (ELI5)
    COMPARE = "compare"               # Create comparison table
    TIMELINE = "timeline"             # Extract chronological events
    PROS_CONS = "pros_cons"           # Analyze advantages/disadvantages
    KEY_POINTS = "key_points"         # Extract bullet points
    CODE_EXAMPLE = "code_example"     # Add practical code examples
    DEEP_DIVE = "deep_dive"           # Expand on a specific section


class TransformRequest(BaseModel):
    """Request to transform research content."""
    action: QuickActionType = Field(
        ...,
        description="The transformation action to apply"
    )
    target_text: str | None = Field(
        None,
        description="Specific section to transform (for deep_dive). If not provided, transforms the full answer."
    )
    context: str | None = Field(
        None,
        description="Additional context (e.g., items to compare, topic for pros/cons)"
    )
    language: str = Field(
        default="python",
        description="Programming language for code_example action"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "action": "summarize"
                },
                {
                    "action": "explain"
                },
                {
                    "action": "compare",
                    "context": "Python vs JavaScript"
                },
                {
                    "action": "code_example",
                    "language": "typescript"
                },
                {
                    "action": "deep_dive",
                    "target_text": "The section about quantum entanglement"
                }
            ]
        }
    }


class TransformResponse(BaseModel):
    """Response from a transform action."""
    session_id: str = Field(..., description="Session ID of the original research")
    action: QuickActionType = Field(..., description="The action that was performed")
    original_length: int = Field(..., description="Character length of original content")
    transformed_content: str = Field(..., description="The transformed content")
    transformed_length: int = Field(..., description="Character length of transformed content")
    duration_ms: int = Field(..., description="Time taken for transformation")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the transformation"
    )


# =============================================================================
# CONVERSATION THREADING SCHEMAS
# =============================================================================

class ConversationNodeResponse(BaseModel):
    """A node in the conversation tree."""
    id: str = Field(..., description="Unique node identifier")
    session_id: str = Field(..., description="Session this node belongs to")
    query: str = Field(..., description="User's query")
    response: str = Field(..., description="Research response (may be truncated)")
    sources: list[str] = Field(default_factory=list, description="Source URLs")
    parent_id: str | None = Field(None, description="Parent node ID if this is a branch")
    children: list[str] = Field(default_factory=list, description="Child node IDs")
    created_at: datetime = Field(..., description="When this node was created")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationTreeInfoResponse(BaseModel):
    """Summary information about a conversation tree."""
    root_id: str = Field(..., description="ID of the root node")
    session_id: str = Field(..., description="Session ID")
    total_nodes: int = Field(..., description="Total nodes in tree")
    max_depth: int = Field(..., description="Maximum depth of tree")
    branch_count: int = Field(..., description="Number of branches")
    created_at: datetime = Field(..., description="When conversation started")
    last_activity: datetime = Field(..., description="Most recent activity")


class ConversationTreeResponse(BaseModel):
    """Full conversation tree."""
    session_id: str = Field(..., description="Session ID")
    info: ConversationTreeInfoResponse | None = Field(None, description="Tree summary")
    nodes: list[ConversationNodeResponse] = Field(
        default_factory=list,
        description="All nodes in the tree"
    )


class BranchRequest(BaseModel):
    """Request to create a new branch from a conversation node."""
    node_id: str = Field(..., description="Node ID to branch from")
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The query for the new branch"
    )
    mode: str = Field(
        default="balanced",
        pattern="^(quick|balanced|full|research|deep)$",
        description="Research mode for the new branch"
    )


class ContextChainResponse(BaseModel):
    """Conversation context chain for a node."""
    node_id: str = Field(..., description="Target node ID")
    chain: list[ConversationNodeResponse] = Field(
        default_factory=list,
        description="Nodes from root to target (oldest first)"
    )
    formatted_context: str = Field(
        default="",
        description="Formatted context string for LLM"
    )

