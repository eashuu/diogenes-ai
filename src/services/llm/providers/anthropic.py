"""
Anthropic (Claude) LLM provider implementation.
"""

import json
import time
from typing import Optional, AsyncGenerator, Type, TypeVar

import httpx
from pydantic import BaseModel

from src.services.llm.base import LLMService
from src.services.llm.models import (
    LLMConfig,
    LLMMessage,
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


class AnthropicProvider(LLMService):
    """
    Anthropic LLM provider for Claude models.
    """

    ANTHROPIC_API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-20250514",
        timeout: float = 120.0,
        max_tokens: int = 4096,
    ):
        if not api_key:
            raise ValueError("Anthropic API key is required")
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.default_model = default_model
        self.timeout = timeout
        self.default_max_tokens = max_tokens
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.ANTHROPIC_API_VERSION,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _build_config(self, config: Optional[LLMConfig] = None) -> LLMConfig:
        if config is None:
            return LLMConfig(
                model=self.default_model,
                max_tokens=self.default_max_tokens,
            )
        return config

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        config = self._build_config(config)
        model = config.model or self.default_model
        start_time = time.time()

        payload = {
            "model": model,
            "max_tokens": config.max_tokens or self.default_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        if system:
            payload["system"] = system

        try:
            client = await self._get_client()
            response = await client.post("/messages", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Anthropic", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            if e.response.status_code == 401:
                raise LLMError("Invalid Anthropic API key", code="LLM_AUTH_ERROR")
            if e.response.status_code == 429:
                raise LLMError("Anthropic rate limit exceeded", code="LLM_RATE_LIMIT")
            raise LLMError(f"Anthropic request failed: {e.response.status_code}", code="LLM_HTTP_ERROR")

        generation_time = time.time() - start_time

        # Extract content from Anthropic response format
        content_blocks = data.get("content", [])
        content = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )
        usage_data = data.get("usage", {})

        usage = TokenUsage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
        )

        return GenerationResult(
            content=content,
            model=model,
            usage=usage,
            generation_time=generation_time,
            finish_reason=data.get("stop_reason"),
        )

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        config = self._build_config(config)
        model = config.model or self.default_model

        payload = {
            "model": model,
            "max_tokens": config.max_tokens or self.default_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "stream": True,
        }
        if system:
            payload["system"] = system

        try:
            client = await self._get_client()
            async with client.stream("POST", "/messages", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            token = delta.get("text", "")
                            if token:
                                yield token
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Anthropic", str(e))

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> T:
        config = self._build_config(config)
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        structured_system = (
            f"You must respond with valid JSON matching this schema:\n\n"
            f"{schema_json}\n\n{system or ''}\n\n"
            f"IMPORTANT: Respond ONLY with valid JSON, no other text."
        )
        result = await self.generate(prompt=prompt, system=structured_system, config=config)
        try:
            data = json.loads(result.content)
            parsed = output_schema.model_validate(data)
            result.parsed = parsed
            return parsed
        except json.JSONDecodeError as e:
            raise LLMGenerationError(config.model or self.default_model, f"Invalid JSON: {e}")
        except Exception as e:
            raise LLMGenerationError(config.model or self.default_model, f"Schema validation failed: {e}")

    async def chat(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        config = self._build_config(config)
        model = config.model or self.default_model
        start_time = time.time()

        # Convert to Anthropic format: system is separate, only user/assistant in messages
        system_msg = None
        anthropic_messages = []
        for m in messages:
            if m.role.value == "system":
                system_msg = m.content
            else:
                anthropic_messages.append(m.to_dict())

        payload = {
            "model": model,
            "max_tokens": config.max_tokens or self.default_max_tokens,
            "messages": anthropic_messages,
            "temperature": config.temperature,
        }
        if system_msg:
            payload["system"] = system_msg

        try:
            client = await self._get_client()
            response = await client.post("/messages", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Anthropic", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            raise LLMError(f"Anthropic chat failed: {e.response.status_code}", code="LLM_HTTP_ERROR")

        generation_time = time.time() - start_time
        content_blocks = data.get("content", [])
        content = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )
        usage_data = data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
        )

        return GenerationResult(
            content=content, model=model, usage=usage, generation_time=generation_time,
            finish_reason=data.get("stop_reason"),
        )

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        config = self._build_config(config)
        model = config.model or self.default_model

        system_msg = None
        anthropic_messages = []
        for m in messages:
            if m.role.value == "system":
                system_msg = m.content
            else:
                anthropic_messages.append(m.to_dict())

        payload = {
            "model": model,
            "max_tokens": config.max_tokens or self.default_max_tokens,
            "messages": anthropic_messages,
            "temperature": config.temperature,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        try:
            client = await self._get_client()
            async with client.stream("POST", "/messages", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            token = data.get("delta", {}).get("text", "")
                            if token:
                                yield token
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Anthropic", str(e))

    async def count_tokens(self, text: str) -> int:
        from src.processing.chunker import count_tokens
        return count_tokens(text)

    async def list_models(self) -> list[str]:
        return [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-5-haiku-20241022",
        ]

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            # Anthropic doesn't have a health endpoint; try a minimal request
            response = await client.post(
                "/messages",
                json={
                    "model": self.default_model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            return response.status_code == 200
        except Exception:
            return False
