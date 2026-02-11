"""
Memory Agent.

Responsible for extracting, managing, and retrieving user memories.
Provides ChatGPT-like memory functionality for personalized research.
"""

from dataclasses import dataclass
from typing import Any

from src.core.agents.base import BaseAgent, AgentCapability
from src.core.agents.protocol import TaskAssignment, TaskResult
from src.services.llm.ollama import OllamaService
from src.storage.memory_store import (
    MemoryStore,
    MemoryType,
    MemoryPriority,
    UserMemory
)
from src.utils.logging import get_logger


logger = get_logger(__name__)


# Prompts for memory extraction
MEMORY_EXTRACTION_PROMPT = """You are a memory extraction assistant. Your job is to identify key facts, preferences, and context from user queries and research interactions that should be remembered for future sessions.

Analyze the following research query and any additional context. Extract memories that would be useful for personalizing future research.

Types of memories to extract:
1. FACT - Personal facts about the user (profession, expertise, interests)
2. PREFERENCE - User preferences (source types, communication style, depth of research)
3. CONTEXT - Domain-specific context (ongoing projects, research topics)
4. INSTRUCTION - Standing instructions (always include citations, prefer academic sources)

For each memory, provide:
- type: The memory type (fact, preference, context, instruction)
- key: A short descriptive key (3-7 words)
- value: The full memory content
- priority: low, medium, high, or critical

Query: {query}
Additional Context: {context}

Respond in JSON format:
{{
    "memories": [
        {{"type": "preference", "key": "preferred sources", "value": "User prefers academic and peer-reviewed sources", "priority": "high"}},
        ...
    ],
    "reasoning": "Brief explanation of why these memories were extracted"
}}

If no significant memories should be extracted, respond with:
{{
    "memories": [],
    "reasoning": "No significant personal information or preferences detected"
}}
"""

MEMORY_RELEVANCE_PROMPT = """Given the following user memories and a new research query, identify which memories are most relevant to include as context.

User Memories:
{memories}

New Research Query: {query}

Select the most relevant memories (up to 5) and explain why they're relevant.
Respond in JSON format:
{{
    "relevant_memory_ids": ["mem_xxx", "mem_yyy"],
    "reasoning": "Brief explanation of relevance"
}}
"""


@dataclass
class MemoryExtractionResult:
    """Result of memory extraction."""
    extracted_memories: list[UserMemory]
    reasoning: str
    raw_response: str


@dataclass 
class MemoryContext:
    """Memory context for research."""
    memories: list[UserMemory]
    context_string: str
    memory_count: int


class MemoryAgent(BaseAgent):
    """
    Agent responsible for user memory management.
    
    Capabilities:
    - Extract memories from user queries and interactions
    - Retrieve relevant memories for research context
    - Manage memory lifecycle (add, update, delete)
    - Build context strings for LLM prompts
    """
    
    def __init__(
        self,
        llm_service: OllamaService | None = None,
        memory_store: MemoryStore | None = None,
        agent_id: str | None = None
    ):
        """
        Initialize Memory Agent.
        
        Args:
            llm_service: LLM service for memory extraction
            memory_store: Storage for memories
            agent_id: Optional agent ID
        """
        super().__init__(
            agent_type="memory",
            capabilities=[AgentCapability.PROCESSING],
            agent_id=agent_id
        )
        
        self._llm_service = llm_service
        self._memory_store = memory_store or MemoryStore()
        self._auto_extract = True  # Auto-extract memories from queries
    
    @property
    def llm_service(self) -> OllamaService:
        """Get LLM service, creating if needed."""
        if self._llm_service is None:
            from src.services.llm.ollama import OllamaService
            self._llm_service = OllamaService()
        return self._llm_service
    
    @property
    def memory_store(self) -> MemoryStore:
        """Get memory store."""
        return self._memory_store
    
    async def execute(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a memory-related task.
        
        Supported task types:
        - extract_memories: Extract memories from query/context
        - get_context: Get relevant memories for a query
        - add_memory: Manually add a memory
        - list_memories: List all user memories
        - delete_memory: Delete a memory
        """
        task_type = task.inputs.get("task_type", "get_context")
        user_id = task.inputs.get("user_id", MemoryStore.DEFAULT_USER)
        
        try:
            if task_type == "extract_memories":
                result = await self._extract_memories(
                    user_id=user_id,
                    query=task.inputs.get("query", ""),
                    context=task.inputs.get("context", ""),
                    session_id=task.inputs.get("session_id")
                )
                return self._success_result(task.task_id, {
                    "extracted_count": len(result.extracted_memories),
                    "memories": [m.to_dict() for m in result.extracted_memories],
                    "reasoning": result.reasoning
                })
            
            elif task_type == "get_context":
                context = await self._get_memory_context(
                    user_id=user_id,
                    query=task.inputs.get("query", ""),
                    max_memories=task.inputs.get("max_memories", 10)
                )
                return self._success_result(task.task_id, {
                    "context_string": context.context_string,
                    "memory_count": context.memory_count,
                    "memories": [m.to_dict() for m in context.memories]
                })
            
            elif task_type == "add_memory":
                memory = await self._add_memory(
                    user_id=user_id,
                    memory_type=MemoryType(task.inputs.get("memory_type", "fact")),
                    key=task.inputs.get("key", ""),
                    value=task.inputs.get("value", ""),
                    priority=MemoryPriority(task.inputs.get("priority", "medium"))
                )
                return self._success_result(task.task_id, {
                    "memory": memory.to_dict()
                })
            
            elif task_type == "list_memories":
                memories = await self._memory_store.get_user_memories(
                    user_id=user_id,
                    memory_type=MemoryType(task.inputs["memory_type"]) if task.inputs.get("memory_type") else None,
                    limit=task.inputs.get("limit", 50)
                )
                return self._success_result(task.task_id, {
                    "memories": [m.to_dict() for m in memories],
                    "count": len(memories)
                })
            
            elif task_type == "delete_memory":
                success = await self._memory_store.delete(
                    task.inputs.get("memory_id", "")
                )
                return self._success_result(task.task_id, {
                    "deleted": success
                })
            
            elif task_type == "update_memory":
                memory = await self._memory_store.update_memory(
                    memory_id=task.inputs.get("memory_id", ""),
                    value=task.inputs.get("value"),
                    priority=MemoryPriority(task.inputs["priority"]) if task.inputs.get("priority") else None
                )
                return self._success_result(task.task_id, {
                    "memory": memory.to_dict() if memory else None,
                    "success": memory is not None
                })
            
            else:
                return TaskResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    status="failed",
                    errors=[f"Unknown task type: {task_type}"],
                    confidence=0.0
                )
                
        except Exception as e:
            logger.error(f"Memory agent error: {e}", exc_info=True)
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)],
                confidence=0.0
            )
    
    def _success_result(self, task_id: str, output: dict) -> TaskResult:
        """Create a success result."""
        return TaskResult(
            task_id=task_id,
            agent_id=self.agent_id,
            status="success",
            outputs=output,
            confidence=1.0
        )
    
    async def _extract_memories(
        self,
        user_id: str,
        query: str,
        context: str = "",
        session_id: str | None = None,
        store: bool = True,
    ) -> MemoryExtractionResult:
        """
        Extract memories from a query/context using LLM.
        
        Args:
            user_id: User identifier
            query: Research query
            context: Additional context
            session_id: Source session ID
            store: Whether to persist extracted memories (False = dry-run)
            
        Returns:
            MemoryExtractionResult with extracted memories
        """
        prompt = MEMORY_EXTRACTION_PROMPT.format(
            query=query,
            context=context or "None provided"
        )
        
        try:
            result = await self.llm_service.generate(prompt)
            response = result.content
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                logger.warning("No JSON found in memory extraction response")
                return MemoryExtractionResult(
                    extracted_memories=[],
                    reasoning="Failed to parse LLM response",
                    raw_response=response
                )
            
            data = json.loads(json_match.group())
            memories_data = data.get("memories", [])
            reasoning = data.get("reasoning", "")
            
            extracted_memories = []
            for mem_data in memories_data:
                if not mem_data.get("key") or not mem_data.get("value"):
                    continue
                
                if store:
                    # Persist to store
                    memory = await self._memory_store.add_memory(
                        user_id=user_id,
                        memory_type=MemoryType(mem_data.get("type", "fact")),
                        key=mem_data["key"],
                        value=mem_data["value"],
                        priority=MemoryPriority(mem_data.get("priority", "medium")),
                        source_session=session_id,
                        metadata={"auto_extracted": True}
                    )
                    extracted_memories.append(memory)
                else:
                    # Dry-run: build transient UserMemory objects without persisting
                    import uuid as _uuid
                    transient = UserMemory(
                        memory_id=f"preview_{_uuid.uuid4().hex[:8]}",
                        user_id=user_id,
                        memory_type=MemoryType(mem_data.get("type", "fact")),
                        key=mem_data["key"],
                        value=mem_data["value"],
                        priority=MemoryPriority(mem_data.get("priority", "medium")),
                        source_session=session_id,
                        metadata={"auto_extracted": True, "preview": True}
                    )
                    extracted_memories.append(transient)
            
            action = "Extracted and stored" if store else "Extracted (preview, not stored)"
            logger.info(f"{action} {len(extracted_memories)} memories for user {user_id}")
            
            return MemoryExtractionResult(
                extracted_memories=extracted_memories,
                reasoning=reasoning,
                raw_response=response
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse memory extraction JSON: {e}")
            return MemoryExtractionResult(
                extracted_memories=[],
                reasoning=f"JSON parse error: {e}",
                raw_response=response if 'response' in locals() else ""
            )
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}", exc_info=True)
            return MemoryExtractionResult(
                extracted_memories=[],
                reasoning=f"Extraction error: {e}",
                raw_response=""
            )
    
    async def _get_memory_context(
        self,
        user_id: str,
        query: str = "",
        max_memories: int = 10
    ) -> MemoryContext:
        """
        Get relevant memory context for a research query.
        
        Args:
            user_id: User identifier
            query: Research query
            max_memories: Maximum memories to include
            
        Returns:
            MemoryContext with relevant memories
        """
        memories = await self._memory_store.get_context_memories(
            user_id=user_id,
            query=query,
            max_memories=max_memories
        )
        
        context_string = await self._memory_store.build_context_string(
            user_id=user_id,
            query=query,
            max_memories=max_memories
        )
        
        return MemoryContext(
            memories=memories,
            context_string=context_string,
            memory_count=len(memories)
        )
    
    async def _add_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        key: str,
        value: str,
        priority: MemoryPriority = MemoryPriority.MEDIUM
    ) -> UserMemory:
        """
        Manually add a memory.
        
        Args:
            user_id: User identifier
            memory_type: Type of memory
            key: Memory key
            value: Memory value
            priority: Memory priority
            
        Returns:
            Created UserMemory
        """
        return await self._memory_store.add_memory(
            user_id=user_id,
            memory_type=memory_type,
            key=key,
            value=value,
            priority=priority,
            metadata={"manual": True}
        )
    
    # ==================== Convenience Methods ====================
    
    async def remember(
        self,
        user_id: str,
        key: str,
        value: str,
        memory_type: MemoryType = MemoryType.FACT,
        priority: MemoryPriority = MemoryPriority.MEDIUM
    ) -> UserMemory:
        """
        Quick method to add a memory.
        
        Example:
            await memory_agent.remember("user123", "profession", "Data scientist at Google")
        """
        return await self._add_memory(
            user_id=user_id,
            memory_type=memory_type,
            key=key,
            value=value,
            priority=priority
        )
    
    async def recall(
        self,
        user_id: str,
        query: str = "",
        max_memories: int = 10
    ) -> str:
        """
        Quick method to get memory context string.
        
        Example:
            context = await memory_agent.recall("user123", "machine learning")
        """
        context = await self._get_memory_context(
            user_id=user_id,
            query=query,
            max_memories=max_memories
        )
        return context.context_string
    
    async def forget(self, memory_id: str) -> bool:
        """
        Quick method to delete a memory.
        
        Example:
            await memory_agent.forget("mem_abc123")
        """
        return await self._memory_store.delete(memory_id)
    
    async def list_all(self, user_id: str) -> list[UserMemory]:
        """
        List all memories for a user.
        
        Example:
            memories = await memory_agent.list_all("user123")
        """
        return await self._memory_store.get_user_memories(user_id=user_id)
    
    async def set_preference(
        self,
        user_id: str,
        key: str,
        value: str,
        priority: MemoryPriority = MemoryPriority.HIGH
    ) -> UserMemory:
        """
        Set a user preference.
        
        Example:
            await memory_agent.set_preference("user123", "source_preference", "academic papers only")
        """
        return await self._add_memory(
            user_id=user_id,
            memory_type=MemoryType.PREFERENCE,
            key=key,
            value=value,
            priority=priority
        )
    
    async def add_instruction(
        self,
        user_id: str,
        instruction: str,
        priority: MemoryPriority = MemoryPriority.HIGH
    ) -> UserMemory:
        """
        Add a standing instruction.
        
        Example:
            await memory_agent.add_instruction("user123", "Always cite sources in APA format")
        """
        return await self._add_memory(
            user_id=user_id,
            memory_type=MemoryType.INSTRUCTION,
            key="instruction",
            value=instruction,
            priority=priority
        )
