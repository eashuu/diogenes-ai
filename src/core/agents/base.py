"""
Base Agent Classes.

Provides the abstract base class for all agents in the multi-agent system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import uuid
import time
import asyncio

from src.utils.logging import get_logger
from src.core.agents.protocol import (
    TaskAssignment,
    TaskResult,
    AgentMessage,
    MessageType,
    Priority,
)


logger = get_logger(__name__)


class AgentCapability(str, Enum):
    """Capabilities that agents can have."""
    PLANNING = "planning"
    SEARCHING = "searching"
    CRAWLING = "crawling"
    PROCESSING = "processing"
    VERIFICATION = "verification"
    SYNTHESIS = "synthesis"
    REVIEW = "review"
    COORDINATION = "coordination"


class AgentStatus(str, Enum):
    """Current status of an agent."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMetrics:
    """Metrics for agent performance tracking."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time_ms: float = 0.0
    average_confidence: float = 0.0
    last_active: Optional[float] = None
    
    def record_task(self, result: TaskResult):
        """Record metrics from a task result."""
        if result.is_success or result.is_partial:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        self.total_execution_time_ms += result.duration_ms
        
        # Update average confidence
        total_tasks = self.tasks_completed + self.tasks_failed
        self.average_confidence = (
            (self.average_confidence * (total_tasks - 1) + result.confidence) 
            / total_tasks
        )
        
        self.last_active = time.time()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 1.0
        return self.tasks_completed / total
    
    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_execution_time_ms": self.total_execution_time_ms,
            "average_confidence": self.average_confidence,
            "last_active": self.last_active,
            "success_rate": self.success_rate,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Each agent has:
    - A unique ID
    - A type identifier
    - A set of capabilities
    - Methods to execute tasks
    - Metrics tracking
    """
    
    def __init__(
        self,
        agent_type: str,
        capabilities: list[AgentCapability],
        agent_id: Optional[str] = None
    ):
        """
        Initialize the agent.
        
        Args:
            agent_type: Type identifier for this agent
            capabilities: List of capabilities this agent has
            agent_id: Optional specific ID, generated if not provided
        """
        self.agent_id = agent_id or f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.capabilities = set(capabilities)
        self.status = AgentStatus.IDLE
        self.metrics = AgentMetrics()
        self._current_task: Optional[TaskAssignment] = None
    
    @abstractmethod
    async def execute(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a task assignment.
        
        This is the main entry point for task execution.
        Subclasses must implement this method.
        
        Args:
            task: The task to execute
            
        Returns:
            Result of the task execution
        """
        pass
    
    def can_handle(self, task: TaskAssignment) -> bool:
        """
        Check if this agent can handle a task.
        
        Args:
            task: The task to check
            
        Returns:
            True if this agent can handle the task
        """
        # Default: check if agent type matches
        return task.agent_type == self.agent_type
    
    async def execute_with_tracking(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a task with metrics tracking.
        
        Wraps the execute method with timing and status updates.
        
        Args:
            task: The task to execute
            
        Returns:
            Result of the task execution
        """
        start_time = time.time()
        self.status = AgentStatus.BUSY
        self._current_task = task
        
        try:
            logger.debug(f"Agent {self.agent_id} starting task {task.task_id}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(task),
                timeout=task.timeout
            )
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            
            # Record metrics
            self.metrics.record_task(result)
            
            logger.debug(
                f"Agent {self.agent_id} completed task {task.task_id} "
                f"in {duration_ms:.0f}ms (status: {result.status})"
            )
            
            return result
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            result = TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[f"Task timed out after {task.timeout}s"],
                duration_ms=duration_ms
            )
            self.metrics.record_task(result)
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Agent {self.agent_id} failed task {task.task_id}: {e}")
            result = TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)],
                duration_ms=duration_ms
            )
            self.metrics.record_task(result)
            return result
            
        finally:
            self.status = AgentStatus.IDLE
            self._current_task = None
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Handle an incoming message.
        
        Override this method to handle inter-agent communication.
        
        Args:
            message: The incoming message
            
        Returns:
            Optional response message
        """
        if message.message_type == MessageType.REQUEST:
            # Convert message to task and execute
            task = TaskAssignment(
                task_type=message.payload.get("task_type"),
                agent_type=self.agent_type,
                inputs=message.payload.get("inputs", {}),
                priority=message.priority,
                timeout=message.payload.get("timeout", 60.0)
            )
            
            result = await self.execute_with_tracking(task)
            
            return message.create_response(
                payload={"result": result.__dict__},
                message_type=MessageType.RESPONSE
            )
        
        return None
    
    def get_status_info(self) -> dict[str, Any]:
        """Get current status information."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "success_rate": self.metrics.success_rate,
                "average_confidence": self.metrics.average_confidence,
            },
            "current_task": self._current_task.task_id if self._current_task else None
        }


class AgentPool:
    """
    Pool of agents for task distribution.
    
    Manages multiple agents and routes tasks to appropriate agents.
    """
    
    def __init__(self):
        """Initialize the agent pool."""
        self._agents: dict[str, BaseAgent] = {}
        self._agents_by_type: dict[str, list[BaseAgent]] = {}
    
    def register(self, agent: BaseAgent):
        """
        Register an agent with the pool.
        
        Args:
            agent: The agent to register
        """
        self._agents[agent.agent_id] = agent
        
        if agent.agent_type not in self._agents_by_type:
            self._agents_by_type[agent.agent_type] = []
        self._agents_by_type[agent.agent_type].append(agent)
        
        logger.info(f"Registered agent {agent.agent_id} ({agent.agent_type})")
    
    def unregister(self, agent_id: str):
        """
        Unregister an agent from the pool.
        
        Args:
            agent_id: ID of the agent to unregister
        """
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            if agent.agent_type in self._agents_by_type:
                self._agents_by_type[agent.agent_type] = [
                    a for a in self._agents_by_type[agent.agent_type]
                    if a.agent_id != agent_id
                ]
            logger.info(f"Unregistered agent {agent_id}")
    
    def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """
        Get an available agent of the specified type.
        
        Prefers idle agents over busy ones.
        
        Args:
            agent_type: Type of agent needed
            
        Returns:
            An available agent, or None if none available
        """
        agents = self._agents_by_type.get(agent_type, [])
        
        # Prefer idle agents
        for agent in agents:
            if agent.status == AgentStatus.IDLE:
                return agent
        
        # Fall back to any agent
        if agents:
            return agents[0]
        
        return None
    
    def get_all_agents(self, agent_type: Optional[str] = None) -> list[BaseAgent]:
        """
        Get all agents, optionally filtered by type.
        
        Args:
            agent_type: Optional type filter
            
        Returns:
            List of agents
        """
        if agent_type:
            return self._agents_by_type.get(agent_type, [])
        return list(self._agents.values())
    
    @property
    def available_agents(self) -> list[str]:
        """Get list of available agent types."""
        return list(self._agents_by_type.keys())
    
    async def execute_task(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a task using an appropriate agent.
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        agent = self.get_agent(task.agent_type)
        
        if agent is None:
            return TaskResult(
                task_id=task.task_id,
                agent_id="pool",
                status="failed",
                errors=[f"No agent available for type: {task.agent_type}"]
            )
        
        return await agent.execute_with_tracking(task)
    
    def get_pool_status(self) -> dict[str, Any]:
        """Get status of all agents in the pool."""
        return {
            "total_agents": len(self._agents),
            "agents_by_type": {
                agent_type: len(agents)
                for agent_type, agents in self._agents_by_type.items()
            },
            "agents": [
                agent.get_status_info()
                for agent in self._agents.values()
            ]
        }
