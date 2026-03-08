"""
OpenAI LLM provider implementation.

Supports OpenAI API and Azure OpenAI endpoints.
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


class OpenAIProvider(LLMService):
    """
    OpenAI LLM provider.

    Supports GPT-4o, GPT-4o-mini, o1, o3, and other OpenAI models.
    Also supports Azure OpenAI via base_url override.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
        timeout: float = 120.0,
        organization: Optional[str] = None,
    ):
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self.organization = organization
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            if self.organization:
                headers["OpenAI-Organization"] = self.organization
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                base_url=self.base_url,
                headers=headers,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _build_config(self, config: Optional[LLMConfig] = None) -> LLMConfig:
        if config is None:
            return LLMConfig(model=self.default_model)
        return config

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        config = self._build_config(config)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self._chat_completion(messages, config)

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        config = self._build_config(config)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async for token in self._chat_completion_stream(messages, config):
            yield token

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

        payload_extra = {"response_format": {"type": "json_object"}}
        messages = [
            {"role": "system", "content": structured_system},
            {"role": "user", "content": prompt},
        ]
        result = await self._chat_completion(messages, config, extra=payload_extra)

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
        msg_dicts = [m.to_dict() for m in messages]
        return await self._chat_completion(msg_dicts, config)

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        config = self._build_config(config)
        msg_dicts = [m.to_dict() for m in messages]
        async for token in self._chat_completion_stream(msg_dicts, config):
            yield token

    async def _chat_completion(
        self,
        messages: list[dict],
        config: LLMConfig,
        extra: Optional[dict] = None,
    ) -> GenerationResult:
        model = config.model or self.default_model
        start_time = time.time()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": False,
        }
        if config.seed is not None:
            payload["seed"] = config.seed
        if extra:
            payload.update(extra)

        try:
            client = await self._get_client()
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("OpenAI", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            if e.response.status_code == 401:
                raise LLMError("Invalid OpenAI API key", code="LLM_AUTH_ERROR")
            if e.response.status_code == 429:
                raise LLMError("OpenAI rate limit exceeded", code="LLM_RATE_LIMIT")
            raise LLMError(f"OpenAI request failed: {e.response.status_code}", code="LLM_HTTP_ERROR")

        generation_time = time.time() - start_time
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage_data = data.get("usage", {})

        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return GenerationResult(
            content=content,
            model=model,
            usage=usage,
            generation_time=generation_time,
            finish_reason=choice.get("finish_reason"),
        )

    async def _chat_completion_stream(
        self,
        messages: list[dict],
        config: LLMConfig,
    ) -> AsyncGenerator[str, None]:
        model = config.model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("OpenAI", str(e))

    async def count_tokens(self, text: str) -> int:
        from src.processing.chunker import count_tokens
        return count_tokens(text)

    async def list_models(self) -> list[str]:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", []) if m.get("id")]
        except Exception as e:
            logger.error(f"Failed to list OpenAI models: {e}")
            return []

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False
