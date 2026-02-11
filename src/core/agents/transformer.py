"""
Transformer Agent.

Handles quick content transformations on research results:
- Summarize: Condense content to key points
- Explain: Simplify explanation (ELI5)
- Compare: Create comparison tables
- Timeline: Extract chronological events
- Pros/Cons: Analyze advantages/disadvantages
- Key Points: Extract bullet points

Matches Perplexity AI's quick action features.
"""

import re
import json
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

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


class QuickAction(str, Enum):
    """Available quick action transformations."""
    SUMMARIZE = "summarize"           # Condense to key points
    EXPLAIN_SIMPLE = "explain"        # Simplify explanation (ELI5)
    COMPARE = "compare"               # Create comparison table
    TIMELINE = "timeline"             # Extract chronological events
    PROS_CONS = "pros_cons"           # Analyze advantages/disadvantages
    KEY_POINTS = "key_points"         # Extract bullet points
    CODE_EXAMPLE = "code_example"     # Add practical code examples
    DEEP_DIVE = "deep_dive"           # Expand on a specific section


# Prompts for each quick action
SUMMARIZE_PROMPT = """Condense the following content into a brief summary.

ORIGINAL CONTENT:
{content}

Requirements:
1. Capture the main point in 1-2 sentences
2. Include 3-5 key takeaways as bullet points
3. Preserve the most important facts and citations
4. Keep it under 150 words

Format:
## Summary
[Brief summary]

### Key Takeaways
- [Point 1]
- [Point 2]
- [Point 3]
"""

EXPLAIN_SIMPLE_PROMPT = """Explain the following content in simple terms that anyone can understand.

ORIGINAL CONTENT:
{content}

Requirements:
1. Use simple, everyday language (explain like I'm 10)
2. Avoid jargon and technical terms (or define them simply)
3. Use analogies and examples from daily life
4. Keep sentences short and clear
5. Maintain accuracy while simplifying

Format the response as an easy-to-read explanation.
"""

COMPARE_PROMPT = """Create a comparison table from the following content.

ORIGINAL CONTENT:
{content}

ITEMS TO COMPARE (if specified):
{compare_items}

Requirements:
1. Identify the main items/options being compared
2. Extract relevant comparison criteria
3. Create a markdown table with clear headers
4. Include a brief summary after the table
5. Note any trade-offs or recommendations

Format:
## Comparison: [Items]

| Criteria | Item A | Item B | ... |
|----------|--------|--------|-----|
| [Criterion 1] | ... | ... | ... |
| [Criterion 2] | ... | ... | ... |

### Summary
[Brief analysis of the comparison]
"""

TIMELINE_PROMPT = """Extract chronological events from the following content.

ORIGINAL CONTENT:
{content}

Requirements:
1. Identify all dates, time periods, or sequential events
2. Order events chronologically
3. Include brief descriptions for each event
4. Note approximate dates if exact dates aren't given
5. Highlight significant milestones

Format:
## Timeline

| Date/Period | Event | Significance |
|-------------|-------|--------------|
| [Date] | [Event] | [Brief note] |

Or use a list format:
- **[Date]**: [Event description]
"""

PROS_CONS_PROMPT = """Analyze the advantages and disadvantages from the following content.

ORIGINAL CONTENT:
{content}

TOPIC TO ANALYZE (if specified):
{topic}

Requirements:
1. Identify clear advantages (pros)
2. Identify clear disadvantages (cons)
3. Be balanced and objective
4. Include supporting evidence where available
5. Add a brief conclusion with recommendation if applicable

Format:
## Pros and Cons: [Topic]

### ✅ Advantages
- **[Pro 1]**: [Brief explanation]
- **[Pro 2]**: [Brief explanation]

### ❌ Disadvantages
- **[Con 1]**: [Brief explanation]
- **[Con 2]**: [Brief explanation]

### 📊 Verdict
[Brief balanced conclusion]
"""

KEY_POINTS_PROMPT = """Extract the key points from the following content.

ORIGINAL CONTENT:
{content}

Requirements:
1. Identify the 5-7 most important points
2. Each point should be a complete, standalone fact
3. Preserve citations where relevant
4. Order by importance
5. Keep each point concise (1-2 sentences)

Format:
## Key Points

1. **[Main Point]**: [Brief explanation]
2. **[Second Point]**: [Brief explanation]
...
"""

CODE_EXAMPLE_PROMPT = """Add practical code examples for the concepts in the following content.

ORIGINAL CONTENT:
{content}

PROGRAMMING LANGUAGE (if specified):
{language}

Requirements:
1. Create relevant, working code examples
2. Use the specified language (or Python if not specified)
3. Add comments explaining key parts
4. Keep examples concise but complete
5. Include any necessary imports
6. Show common use cases

Format:
## Code Examples

### [Concept 1]
```{language}
[Code with comments]
```

### [Concept 2]
```{language}
[Code with comments]
```
"""

DEEP_DIVE_PROMPT = """Expand on the following section with more detail.

SECTION TO EXPAND:
{target_text}

FULL CONTEXT:
{content}

Requirements:
1. Provide more depth on the specific topic
2. Add relevant details not in the original
3. Include examples or use cases
4. Explain underlying concepts
5. Maintain consistency with the original content

Format the response as a detailed explanation of the topic.
"""


@dataclass
class TransformResult:
    """Result of a quick action transformation."""
    action: QuickAction
    original_length: int
    transformed_content: str
    transformed_length: int
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "original_length": self.original_length,
            "transformed_content": self.transformed_content,
            "transformed_length": self.transformed_length,
            "metadata": self.metadata
        }


class TransformerAgent(BaseAgent):
    """
    Agent for quick content transformations.
    
    Provides Perplexity-style quick actions:
    - Summarize content
    - Simplify explanations
    - Create comparisons
    - Extract timelines
    - Analyze pros/cons
    - Extract key points
    - Add code examples
    - Deep dive on sections
    """
    
    # Map actions to prompts
    ACTION_PROMPTS = {
        QuickAction.SUMMARIZE: SUMMARIZE_PROMPT,
        QuickAction.EXPLAIN_SIMPLE: EXPLAIN_SIMPLE_PROMPT,
        QuickAction.COMPARE: COMPARE_PROMPT,
        QuickAction.TIMELINE: TIMELINE_PROMPT,
        QuickAction.PROS_CONS: PROS_CONS_PROMPT,
        QuickAction.KEY_POINTS: KEY_POINTS_PROMPT,
        QuickAction.CODE_EXAMPLE: CODE_EXAMPLE_PROMPT,
        QuickAction.DEEP_DIVE: DEEP_DIVE_PROMPT,
    }
    
    def __init__(
        self,
        agent_id: str = "transformer-agent",
        model: Optional[str] = None
    ):
        """
        Initialize TransformerAgent.
        
        Args:
            agent_id: Unique identifier for this agent
            model: LLM model to use (defaults to synthesizer model)
        """
        super().__init__(
            agent_type="transformer",
            capabilities=[AgentCapability.SYNTHESIS],
            agent_id=agent_id
        )
        
        settings = get_settings()
        # Use synthesizer model for quality transformations
        self.model = model or settings.llm.models.synthesizer
        self._llm_service: Optional[OllamaService] = None
    
    @property
    def llm_service(self) -> OllamaService:
        """Lazy-load LLM service."""
        if self._llm_service is None:
            settings = get_settings()
            self._llm_service = OllamaService(
                base_url=settings.llm.base_url,
                default_model=self.model,
                timeout=settings.llm.timeout
            )
        return self._llm_service
    
    async def execute(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a transformation task.
        
        Expected inputs:
            - action: QuickAction enum value or string
            - content: str - The content to transform
            - target_text: str (optional) - Specific section to focus on
            - context: str (optional) - Additional context (e.g., items to compare)
            - language: str (optional) - Programming language for code examples
        """
        import time
        start_time = time.time()
        
        try:
            action_input = task.inputs.get("action")
            content = task.inputs.get("content", "")
            target_text = task.inputs.get("target_text")
            context = task.inputs.get("context", "")
            language = task.inputs.get("language", "python")
            
            # Parse action
            if isinstance(action_input, str):
                try:
                    action = QuickAction(action_input)
                except ValueError:
                    return TaskResult(
                        task_id=task.task_id,
                        agent_id=self.agent_id,
                        status="failed",
                        errors=[f"Unknown action: {action_input}. Valid actions: {[a.value for a in QuickAction]}"]
                    )
            elif isinstance(action_input, QuickAction):
                action = action_input
            else:
                return TaskResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    status="failed",
                    errors=["Missing required input: action"]
                )
            
            if not content:
                return TaskResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    status="failed",
                    errors=["Missing required input: content"]
                )
            
            # Perform transformation
            result = await self._transform(
                action=action,
                content=content,
                target_text=target_text,
                context=context,
                language=language
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                outputs=result.to_dict(),
                confidence=0.9,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}", exc_info=True)
            duration_ms = (time.time() - start_time) * 1000
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)],
                duration_ms=duration_ms
            )
    
    async def _transform(
        self,
        action: QuickAction,
        content: str,
        target_text: Optional[str] = None,
        context: str = "",
        language: str = "python"
    ) -> TransformResult:
        """Perform the actual transformation."""
        logger.info(f"Performing {action.value} transformation")
        
        prompt_template = self.ACTION_PROMPTS[action]
        
        # Build prompt based on action
        if action == QuickAction.COMPARE:
            prompt = prompt_template.format(
                content=content[:8000],
                compare_items=context or "Not specified - identify from content"
            )
        elif action == QuickAction.PROS_CONS:
            prompt = prompt_template.format(
                content=content[:8000],
                topic=context or "The main topic"
            )
        elif action == QuickAction.CODE_EXAMPLE:
            prompt = prompt_template.format(
                content=content[:8000],
                language=language
            )
        elif action == QuickAction.DEEP_DIVE:
            prompt = prompt_template.format(
                content=content[:6000],
                target_text=target_text or content[:1000]
            )
        else:
            prompt = prompt_template.format(content=content[:8000])
        
        # Get system prompt based on action
        system_prompt = self._get_system_prompt(action)
        
        response = await self.llm_service.generate(
            prompt=prompt,
            system=system_prompt
        )
        
        transformed = response.content
        
        return TransformResult(
            action=action,
            original_length=len(content),
            transformed_content=transformed,
            transformed_length=len(transformed),
            metadata={
                "target_text": target_text[:100] if target_text else None,
                "context": context[:100] if context else None,
                "language": language if action == QuickAction.CODE_EXAMPLE else None
            }
        )
    
    def _get_system_prompt(self, action: QuickAction) -> str:
        """Get appropriate system prompt for the action."""
        prompts = {
            QuickAction.SUMMARIZE: "You are an expert at condensing information while preserving key facts.",
            QuickAction.EXPLAIN_SIMPLE: "You are a patient teacher who explains complex topics simply.",
            QuickAction.COMPARE: "You are an analyst who creates clear, objective comparisons.",
            QuickAction.TIMELINE: "You are a historian who organizes events chronologically.",
            QuickAction.PROS_CONS: "You are a balanced analyst who evaluates both sides objectively.",
            QuickAction.KEY_POINTS: "You are an editor who identifies the most important information.",
            QuickAction.CODE_EXAMPLE: "You are a senior developer who writes clean, educational code.",
            QuickAction.DEEP_DIVE: "You are a subject matter expert who provides detailed explanations."
        }
        return prompts.get(action, "You are a helpful assistant.")
    
    async def transform(
        self,
        action: QuickAction | str,
        content: str,
        target_text: Optional[str] = None,
        context: str = "",
        language: str = "python"
    ) -> TransformResult:
        """
        Convenience method to transform content directly.
        
        Args:
            action: The transformation action to perform
            content: The content to transform
            target_text: Specific section to focus on (for DEEP_DIVE)
            context: Additional context (items to compare, topic for pros/cons)
            language: Programming language for code examples
            
        Returns:
            TransformResult with transformed content
        """
        if isinstance(action, str):
            action = QuickAction(action)
        
        task = TaskAssignment(
            task_id="direct-transform",
            task_type=TaskType.FORMAT_OUTPUT,
            agent_type="transformer",
            inputs={
                "action": action,
                "content": content,
                "target_text": target_text,
                "context": context,
                "language": language
            }
        )
        
        result = await self.execute(task)
        
        if result.status == "success":
            return TransformResult(
                action=action,
                original_length=result.outputs.get("original_length", len(content)),
                transformed_content=result.outputs.get("transformed_content", ""),
                transformed_length=result.outputs.get("transformed_length", 0),
                metadata=result.outputs.get("metadata", {})
            )
        else:
            logger.warning(f"Transform failed: {result.errors}")
            return TransformResult(
                action=action,
                original_length=len(content),
                transformed_content="Transformation failed",
                transformed_length=0,
                metadata={"errors": result.errors}
            )


# Convenience function for direct usage
async def quick_transform(
    action: QuickAction | str,
    content: str,
    **kwargs
) -> TransformResult:
    """
    Quick function to transform content.
    
    Args:
        action: The transformation action
        content: Content to transform
        **kwargs: Additional arguments (target_text, context, language)
        
    Returns:
        TransformResult
    """
    agent = TransformerAgent()
    return await agent.transform(action=action, content=content, **kwargs)
