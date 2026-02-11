"""
Ollama LLM service implementation.
"""

import asyncio
from typing import Optional, AsyncGenerator, Type, TypeVar
import json
import time

import httpx
from pydantic import BaseModel

from src.config import get_settings
from src.services.llm.base import LLMService
from src.services.llm.models import (
    LLMConfig,
    LLMMessage,
    LLMRole,
    GenerationResult,
    TokenUsage,
)
from src.utils.exceptions import (
    LLMError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMGenerationError,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaService(LLMService):
    """
    Ollama LLM service implementation.
    
    Provides local LLM inference via Ollama's REST API.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.llm.base_url
        self.default_model = default_model or settings.llm.models.synthesizer
        self.timeout = timeout or settings.llm.timeout
        self.default_temperature = settings.llm.temperature
        self.default_max_tokens = settings.llm.max_tokens
        self._verify_ssl = settings.llm.verify_ssl
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                base_url=self.base_url,
                verify=self._verify_ssl,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _build_config(self, config: Optional[LLMConfig] = None) -> LLMConfig:
        """Build config with defaults."""
        if config is None:
            return LLMConfig(
                model=self.default_model,
                temperature=self.default_temperature,
                max_tokens=self.default_max_tokens,
            )
        return config
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        """
        Generate text from a prompt using Ollama.
        """
        config = self._build_config(config)
        model = config.model or self.default_model
        
        logger.debug(f"Generating with {model}: {prompt[:100]}...")
        start_time = time.time()
        
        # Build request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
            },
        }
        
        if system:
            payload["system"] = system
        
        if config.format == "json":
            payload["format"] = "json"
        
        if config.seed is not None:
            payload["options"]["seed"] = config.seed
        
        try:
            client = await self._get_client()
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            
        except httpx.TimeoutException:
            logger.error(f"LLM timeout for model {model}")
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise LLMConnectionError("Ollama", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise LLMError(
                f"LLM request failed with status {e.response.status_code}",
                code="LLM_HTTP_ERROR",
            )
        
        generation_time = time.time() - start_time
        
        # Parse response
        content = data.get("response", "")
        
        # Extract usage if available
        usage = TokenUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        
        logger.info(
            f"Generated {usage.completion_tokens} tokens with {model} "
            f"in {generation_time:.2f}s"
        )
        
        return GenerationResult(
            content=content,
            model=model,
            usage=usage,
            generation_time=generation_time,
            finish_reason=data.get("done_reason"),
        )
    
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate text with streaming output.
        """
        config = self._build_config(config)
        model = config.model or self.default_model
        
        logger.debug(f"Streaming generation with {model}")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
            },
        }
        
        if system:
            payload["system"] = system
        
        if config.format == "json":
            payload["format"] = "json"
        
        try:
            client = await self._get_client()
            async with client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except httpx.TimeoutException:
            logger.error(f"LLM stream timeout for model {model}")
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise LLMConnectionError("Ollama", str(e))
    
    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> T:
        """
        Generate structured output matching a Pydantic schema.
        """
        config = self._build_config(config)
        
        # Create a system prompt that includes schema info
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        structured_system = f"""You must respond with valid JSON that matches this schema:

{schema_json}

{system or ''}

IMPORTANT: Respond ONLY with valid JSON, no other text."""
        
        # Force JSON format
        config_with_json = LLMConfig(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            format="json",
        )
        
        result = await self.generate(
            prompt=prompt,
            system=structured_system,
            config=config_with_json,
        )
        
        try:
            # Parse JSON and validate against schema
            data = json.loads(result.content)
            parsed = output_schema.model_validate(data)
            
            # Attach parsed result to GenerationResult
            result.parsed = parsed
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {result.content}")
            raise LLMGenerationError(config.model, f"Invalid JSON output: {e}")
        except Exception as e:
            logger.error(f"Failed to validate schema: {e}")
            raise LLMGenerationError(config.model, f"Schema validation failed: {e}")
    
    async def chat(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        """
        Generate response for a conversation.
        """
        config = self._build_config(config)
        model = config.model or self.default_model
        
        logger.debug(f"Chat with {model}: {len(messages)} messages")
        start_time = time.time()
        
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        
        try:
            client = await self._get_client()
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Ollama", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            raise LLMError(f"Chat failed with status {e.response.status_code}")
        
        generation_time = time.time() - start_time
        
        message = data.get("message", {})
        content = message.get("content", "")
        
        usage = TokenUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
        )
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        
        return GenerationResult(
            content=content,
            model=model,
            usage=usage,
            generation_time=generation_time,
        )
    
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response for a conversation.
        """
        config = self._build_config(config)
        model = config.model or self.default_model
        
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        
        try:
            client = await self._get_client()
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        message = data.get("message", {})
                        token = message.get("content", "")
                        if token:
                            yield token
                        
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Ollama", str(e))
    
    async def count_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        Note: This is an approximation. Actual count depends on model tokenizer.
        """
        # Simple approximation: ~4 characters per token
        return len(text) // 4
    
    async def list_models(self) -> list[str]:
        """
        List available models in Ollama.
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            
            models = data.get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    async def pull_model(self, model: str) -> bool:
        """
        Pull a model if not available.
        
        This is a blocking operation that may take a while.
        """
        logger.info(f"Pulling model: {model}")
        
        try:
            client = await self._get_client()
            async with client.stream(
                "POST",
                "/api/pull",
                json={"name": model},
                timeout=httpx.Timeout(600.0),  # 10 minute timeout for pull
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            status = data.get("status", "")
                            logger.debug(f"Pull status: {status}")
                        except json.JSONDecodeError:
                            pass
            
            logger.info(f"Successfully pulled model: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
