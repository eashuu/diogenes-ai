"""
Agent Communication Protocol.

Defines the message types and data structures for inter-agent communication.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime
import uuid


class MessageType(str, Enum):
    """Type of message being sent between agents."""
    REQUEST = "request"       # Task request
    RESPONSE = "response"     # Task response
    UPDATE = "update"         # Progress update
    ERROR = "error"           # Error notification
    COMPLETE = "complete"     # Task completion


class Priority(int, Enum):
    """Priority level for tasks."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskType(str, Enum):
    """Types of tasks agents can perform."""
    # Planning tasks
    CREATE_PLAN = "create_plan"
    DECOMPOSE_QUERY = "decompose_query"
    
    # Research tasks
    WEB_SEARCH = "web_search"
    ACADEMIC_SEARCH = "academic_search"
    CODE_SEARCH = "code_search"
    CRAWL_URLS = "crawl_urls"
    LOAD_DOCUMENTS = "load_documents"
    
    # Processing tasks
    EXTRACT_FACTS = "extract_facts"
    EXTRACT_ENTITIES = "extract_entities"
    CHUNK_CONTENT = "chunk_content"
    SCORE_QUALITY = "score_quality"
    
    # Verification tasks
    VERIFY_CLAIMS = "verify_claims"
    CHECK_CONTRADICTIONS = "check_contradictions"
    ASSESS_RELIABILITY = "assess_reliability"
    
    # Synthesis tasks
    SYNTHESIZE_ANSWER = "synthesize_answer"
    INSERT_CITATIONS = "insert_citations"
    FORMAT_OUTPUT = "format_output"
    
    # Review tasks
    REVIEW_QUALITY = "review_quality"
    IDENTIFY_GAPS = "identify_gaps"
    SUGGEST_IMPROVEMENTS = "suggest_improvements"


@dataclass
class AgentMessage:
    """
    Message for inter-agent communication.
    
    Attributes:
        id: Unique message identifier
        sender: Agent ID of the sender
        recipient: Agent ID of the recipient (or 'broadcast')
        message_type: Type of message
        priority: Priority level
        payload: Message data
        timestamp: When the message was created
        correlation_id: For linking request-response pairs
        ttl: Time to live in seconds (optional)
    """
    sender: str
    recipient: str
    message_type: MessageType
    payload: dict[str, Any]
    priority: Priority = Priority.NORMAL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    ttl: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if the message has expired."""
        if self.ttl is None:
            return False
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.ttl
    
    def create_response(
        self,
        payload: dict[str, Any],
        message_type: MessageType = MessageType.RESPONSE
    ) -> "AgentMessage":
        """Create a response to this message."""
        return AgentMessage(
            sender=self.recipient,
            recipient=self.sender,
            message_type=message_type,
            payload=payload,
            correlation_id=self.id,
            priority=self.priority
        )


@dataclass
class TaskAssignment:
    """
    Task assignment from coordinator to worker agent.
    
    Attributes:
        task_id: Unique task identifier
        task_type: Type of task to perform
        agent_type: Type of agent to handle this task
        inputs: Input data for the task
        constraints: Time limits, quality thresholds, etc.
        dependencies: Task IDs that must complete first
        priority: Task priority
        timeout: Maximum time for task in seconds
    """
    task_type: TaskType
    agent_type: str
    inputs: dict[str, Any]
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    constraints: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    priority: Priority = Priority.NORMAL
    timeout: float = 60.0
    is_critical: bool = False
    
    def has_dependencies(self) -> bool:
        """Check if task has unresolved dependencies."""
        return len(self.dependencies) > 0


@dataclass
class TaskResult:
    """
    Result from worker agent back to coordinator.
    
    Attributes:
        task_id: ID of the completed task
        agent_id: ID of the agent that executed the task
        status: Execution status
        outputs: Result data
        metadata: Additional info (timing, token usage, etc.)
        confidence: Confidence score (0.0 to 1.0)
        errors: List of errors encountered
        duration_ms: Execution time in milliseconds
    """
    task_id: str
    agent_id: str
    status: str  # "success", "partial", "failed"
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    
    @property
    def is_success(self) -> bool:
        """Check if task succeeded."""
        return self.status == "success"
    
    @property
    def is_partial(self) -> bool:
        """Check if task partially succeeded."""
        return self.status == "partial"
    
    @property
    def is_failed(self) -> bool:
        """Check if task failed."""
        return self.status == "failed"
    
    def merge_with(self, other: "TaskResult") -> "TaskResult":
        """Merge results from multiple task executions."""
        return TaskResult(
            task_id=self.task_id,
            agent_id=f"{self.agent_id}+{other.agent_id}",
            status="success" if self.is_success and other.is_success else "partial",
            outputs={**self.outputs, **other.outputs},
            metadata={**self.metadata, **other.metadata},
            confidence=(self.confidence + other.confidence) / 2,
            errors=self.errors + other.errors,
            duration_ms=max(self.duration_ms, other.duration_ms)
        )


@dataclass
class ResearchPlan:
    """
    Research execution plan created by the planner.
    
    Attributes:
        query: Original user query
        intent: Understood intent/goal
        sub_queries: Decomposed search queries
        source_types: Types of sources to search
        strategies: Search strategies to employ
        verification_level: How rigorously to verify facts
        output_format: Desired output format
        time_budget: Total time budget in seconds
        quality_threshold: Minimum quality score
    """
    query: str
    intent: str
    sub_queries: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=lambda: ["web"])
    strategies: list[str] = field(default_factory=lambda: ["general"])
    verification_level: str = "standard"  # "minimal", "standard", "rigorous"
    output_format: str = "prose"  # "prose", "bullets", "structured"
    time_budget: float = 120.0
    quality_threshold: float = 0.6
    key_concepts: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "intent": self.intent,
            "sub_queries": self.sub_queries,
            "source_types": self.source_types,
            "strategies": self.strategies,
            "verification_level": self.verification_level,
            "output_format": self.output_format,
            "time_budget": self.time_budget,
            "quality_threshold": self.quality_threshold,
            "key_concepts": self.key_concepts
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchPlan":
        """Create from dictionary."""
        return cls(
            query=data.get("query", ""),
            intent=data.get("intent", ""),
            sub_queries=data.get("sub_queries", []),
            source_types=data.get("source_types", ["web"]),
            strategies=data.get("strategies", ["general"]),
            verification_level=data.get("verification_level", "standard"),
            output_format=data.get("output_format", "prose"),
            time_budget=data.get("time_budget", 120.0),
            quality_threshold=data.get("quality_threshold", 0.6),
            key_concepts=data.get("key_concepts", [])
        )


@dataclass 
class VerifiedClaim:
    """
    A claim that has been verified against sources.
    
    Attributes:
        claim: The claim text
        status: Verification status
        confidence: Confidence in the verification
        supporting_sources: Sources that support the claim
        contradicting_sources: Sources that contradict the claim
    """
    claim: str
    status: str  # "verified", "disputed", "refuted", "unverified"
    confidence: float = 0.5
    supporting_sources: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)
    
    @property
    def is_verified(self) -> bool:
        return self.status == "verified"
    
    @property
    def is_disputed(self) -> bool:
        return self.status == "disputed"
    
    @property
    def source_count(self) -> int:
        return len(self.supporting_sources) + len(self.contradicting_sources)


@dataclass
class Contradiction:
    """A contradiction between two claims."""
    claim1: str
    claim2: str
    severity: str = "minor"  # "minor", "moderate", "major"
    explanation: str = ""
