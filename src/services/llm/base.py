"""
Abstract base class for LLM services.
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Type, TypeVar

from pydantic import BaseModel

from src.services.llm.models import (
    LLMConfig,
    LLMMessage,
    GenerationResult,
    TokenUsage,
)

T = TypeVar("T", bound=BaseModel)


class LLMService(ABC):
    """
    Abstract interface for LLM providers.
    
    Implementations must provide both streaming and non-streaming
    generation capabilities.
    """
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        """
        Generate text from a prompt.
        
        Args:
            prompt: User prompt
            system: Optional system message
            config: Generation configuration
            
        Returns:
            GenerationResult with generated text
            
        Raises:
            LLMError: If generation fails
            LLMTimeoutError: If generation times out
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate text with streaming output.
        
        Args:
            prompt: User prompt
            system: Optional system message
            config: Generation configuration
            
        Yields:
            Generated tokens one at a time
            
        Raises:
            LLMError: If generation fails
        """
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> T:
        """
        Generate structured output matching a Pydantic schema.
        
        Args:
            prompt: User prompt
            output_schema: Pydantic model class for output
            system: Optional system message
            config: Generation configuration
            
        Returns:
            Parsed Pydantic model instance
            
        Raises:
            LLMError: If generation or parsing fails
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        """
        Generate response for a conversation.
        
        Args:
            messages: List of conversation messages
            config: Generation configuration
            
        Returns:
            GenerationResult with response
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response for a conversation.
        
        Args:
            messages: List of conversation messages
            config: Generation configuration
            
        Yields:
            Generated tokens
        """
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        """
        List available models.
        
        Returns:
            List of model names
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is available.
        
        Returns:
            True if service is healthy
        """
        pass
