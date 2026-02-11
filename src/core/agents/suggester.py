"""
Suggestion Agent.

Generates follow-up questions and related topics based on research results.
Key feature for matching Perplexity AI's UX.
"""

import json
from typing import Any, Optional
from dataclasses import dataclass, field

from src.utils.logging import get_logger
from src.core.agents.base import BaseAgent, AgentCapability
from src.core.agents.protocol import (
    TaskAssignment,
    TaskResult,
    TaskType,
)
from src.services.llm.ollama import OllamaService
from src.config import get_settings


logger = get_logger(__name__)


# Prompt for generating follow-up suggestions
SUGGESTION_PROMPT = """Based on this research, generate helpful follow-up questions and related topics.

ORIGINAL QUERY: {query}

ANSWER SUMMARY:
{answer_summary}

KEY ENTITIES/CONCEPTS:
{entities}

SOURCES USED:
{sources}

Generate:
1. 3-4 follow-up questions the user might want to ask next
   - Questions that go deeper into specific aspects
   - Questions that explore related but not covered topics
   - Questions that apply the information practically
   
2. 3-5 related topics the user might be interested in

Return ONLY valid JSON:
{{
    "suggested_questions": [
        "Question 1?",
        "Question 2?",
        "Question 3?"
    ],
    "related_topics": [
        "Topic 1",
        "Topic 2",
        "Topic 3"
    ]
}}
"""


# Quick suggestion prompt for faster response
QUICK_SUGGESTION_PROMPT = """Given this query and answer, suggest 3 follow-up questions.

Query: {query}
Answer (first 500 chars): {answer_preview}

Return ONLY a JSON array of 3 questions:
["Question 1?", "Question 2?", "Question 3?"]
"""


@dataclass
class SuggestionResult:
    """Result from suggestion generation."""
    suggested_questions: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "suggested_questions": self.suggested_questions,
            "related_topics": self.related_topics,
            "confidence": self.confidence
        }


class SuggestionAgent(BaseAgent):
    """
    Agent for generating follow-up questions and related topics.
    
    This agent analyzes research results and generates:
    1. Suggested follow-up questions based on the answer content
    2. Related topics the user might want to explore
    3. Contextually relevant suggestions using entities and sources
    
    Features:
    - Two modes: full (comprehensive) and quick (fast, minimal)
    - Entity-aware suggestions
    - Source-aware suggestions for academic follow-ups
    """
    
    def __init__(
        self,
        agent_id: str = "suggestion-agent",
        model: Optional[str] = None
    ):
        """
        Initialize SuggestionAgent.
        
        Args:
            agent_id: Unique identifier for this agent
            model: LLM model to use (defaults to fast model from settings)
        """
        super().__init__(
            agent_type="suggester",
            capabilities=[AgentCapability.SYNTHESIS],
            agent_id=agent_id
        )
        
        settings = get_settings()
        # Use planner model for suggestions (fast model for non-quality-critical tasks)
        self.model = model or settings.llm.models.planner
        self._llm_service: Optional[OllamaService] = None
    
    @property
    def llm_service(self) -> OllamaService:
        """Lazy-load LLM service."""
        if self._llm_service is None:
            self._llm_service = OllamaService()
        return self._llm_service
    
    async def execute(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a suggestion generation task.
        
        Expected inputs:
            - query: str - Original research query
            - answer: str - The research answer
            - sources: list[str] - Source titles/URLs (optional)
            - entities: list[str] - Extracted entities (optional)
            - quick: bool - Whether to use quick mode (optional)
        """
        import time
        start_time = time.time()
        
        try:
            query = task.inputs.get("query", "")
            answer = task.inputs.get("answer", "")
            sources = task.inputs.get("sources", [])
            entities = task.inputs.get("entities", [])
            quick_mode = task.inputs.get("quick", False)
            
            if not query or not answer:
                return TaskResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    status="failed",
                    errors=["Missing required inputs: query and answer"]
                )
            
            if quick_mode:
                result = await self._generate_quick_suggestions(query, answer)
            else:
                result = await self._generate_full_suggestions(
                    query, answer, sources, entities
                )
            
            duration_ms = (time.time() - start_time) * 1000
            
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                outputs=result.to_dict(),
                confidence=result.confidence,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}", exc_info=True)
            duration_ms = (time.time() - start_time) * 1000
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)],
                duration_ms=duration_ms
            )
    
    async def _generate_full_suggestions(
        self,
        query: str,
        answer: str,
        sources: list[str],
        entities: list[str]
    ) -> SuggestionResult:
        """Generate comprehensive suggestions with full context."""
        
        # Prepare answer summary (first 1000 chars or key points)
        answer_summary = answer[:1000] + "..." if len(answer) > 1000 else answer
        
        # Format sources
        sources_text = "\n".join(f"- {s}" for s in sources[:10]) if sources else "None provided"
        
        # Format entities
        entities_text = ", ".join(entities[:15]) if entities else "None extracted"
        
        prompt = SUGGESTION_PROMPT.format(
            query=query,
            answer_summary=answer_summary,
            entities=entities_text,
            sources=sources_text
        )
        
        from src.services.llm.models import LLMConfig
        response = await self.llm_service.generate(
            prompt=prompt,
            config=LLMConfig(
                model=self.model,
                temperature=0.7,  # Slightly creative for diverse suggestions
                max_tokens=500,
            ),
        )
        
        return self._parse_suggestions(response.content)
    
    async def _generate_quick_suggestions(
        self,
        query: str,
        answer: str
    ) -> SuggestionResult:
        """Generate quick suggestions with minimal context."""
        
        answer_preview = answer[:500] + "..." if len(answer) > 500 else answer
        
        prompt = QUICK_SUGGESTION_PROMPT.format(
            query=query,
            answer_preview=answer_preview
        )
        
        from src.services.llm.models import LLMConfig
        response = await self.llm_service.generate(
            prompt=prompt,
            config=LLMConfig(
                model=self.model,
                temperature=0.7,
                max_tokens=200,
            ),
        )
        
        # Parse simple array response
        try:
            questions = json.loads(response.content)
            if isinstance(questions, list):
                return SuggestionResult(
                    suggested_questions=questions[:4],
                    related_topics=[],
                    confidence=0.7
                )
        except json.JSONDecodeError:
            pass
        
        # Fallback: try to extract questions from text
        return self._parse_suggestions(response.content)
    
    def _parse_suggestions(self, response_text: str) -> SuggestionResult:
        """Parse LLM response into SuggestionResult."""
        
        result = SuggestionResult(confidence=0.5)
        
        # Try to parse as JSON first
        try:
            # Find JSON in response
            json_match = response_text
            if "```json" in response_text:
                json_match = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_match = response_text.split("```")[1].split("```")[0]
            
            data = json.loads(json_match.strip())
            
            if isinstance(data, dict):
                result.suggested_questions = data.get("suggested_questions", [])[:4]
                result.related_topics = data.get("related_topics", [])[:5]
                result.confidence = 0.85
            elif isinstance(data, list):
                result.suggested_questions = data[:4]
                result.confidence = 0.7
                
        except (json.JSONDecodeError, IndexError):
            # Fallback: extract questions using regex
            import re
            
            # Find lines that look like questions
            questions = re.findall(r'["\']([^"\']+\?)["\']', response_text)
            if not questions:
                questions = re.findall(r'(?:^|\n)\s*[-•\d.]+\s*(.+\?)', response_text)
            
            result.suggested_questions = questions[:4]
            result.confidence = 0.4
        
        # Clean up questions
        result.suggested_questions = [
            q.strip() for q in result.suggested_questions 
            if q.strip() and len(q.strip()) > 10
        ]
        
        result.related_topics = [
            t.strip() for t in result.related_topics 
            if t.strip() and len(t.strip()) > 3
        ]
        
        return result
    
    async def generate_suggestions(
        self,
        query: str,
        answer: str,
        sources: Optional[list[str]] = None,
        entities: Optional[list[str]] = None,
        quick: bool = False
    ) -> SuggestionResult:
        """
        Convenience method to generate suggestions directly.
        
        Args:
            query: The original research query
            answer: The research answer content
            sources: List of source titles/URLs
            entities: List of extracted entities
            quick: Whether to use quick mode
            
        Returns:
            SuggestionResult with questions and topics
        """
        task = TaskAssignment(
            task_id="direct-suggestion",
            task_type=TaskType.SYNTHESIZE_ANSWER,
            agent_type="suggester",
            inputs={
                "query": query,
                "answer": answer,
                "sources": sources or [],
                "entities": entities or [],
                "quick": quick
            }
        )
        
        result = await self.execute(task)
        
        if result.status == "success":
            return SuggestionResult(
                suggested_questions=result.outputs.get("suggested_questions", []),
                related_topics=result.outputs.get("related_topics", []),
                confidence=result.confidence
            )
        else:
            logger.warning(f"Suggestion generation failed: {result.errors}")
            return SuggestionResult()
