"""
LLM service models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal, Any
from enum import Enum


class LLMRole(str, Enum):
    """Message role in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    
    role: LLMRole
    content: str
    
    def to_dict(self) -> dict:
        return {"role": self.role.value, "content": self.content}


@dataclass
class GenerationConfig:
    """Configuration for LLM generation requests.
    
    Note: This is different from src.config.LLMConfig which is for
    application-level LLM service settings.
    """
    
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    top_k: int = 40
    stop_sequences: list[str] = field(default_factory=list)
    
    # Streaming
    stream: bool = False
    
    # Format
    format: Optional[Literal["json"]] = None  # For JSON mode
    
    # Advanced
    seed: Optional[int] = None  # For reproducibility
    num_ctx: int = 8192  # Context window size


# Alias for backward compatibility
LLMConfig = GenerationConfig


@dataclass
class TokenUsage:
    """Token usage statistics."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class GenerationResult:
    """Result of an LLM generation."""
    
    content: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    generation_time: float = 0.0
    finish_reason: Optional[str] = None
    
    # For structured output
    parsed: Optional[Any] = None
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate generation speed."""
        if self.generation_time > 0:
            return self.usage.completion_tokens / self.generation_time
        return 0.0


@dataclass
class StructuredOutputSchema:
    """Schema definition for structured LLM output."""
    
    name: str
    description: str
    schema: dict  # JSON schema
    
    @classmethod
    def from_pydantic(cls, model_class) -> "StructuredOutputSchema":
        """Create from a Pydantic model."""
        return cls(
            name=model_class.__name__,
            description=model_class.__doc__ or "",
            schema=model_class.model_json_schema(),
        )
