"""
Groq LLM provider implementation — optimized for fast inference.
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


class GroqProvider(LLMService):
    """
    Groq LLM provider — uses OpenAI-compatible chat completions API.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "llama-3.3-70b-versatile",
        timeout: float = 60.0,
    ):
        if not api_key:
            raise ValueError("Groq API key is required")
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.default_model = default_model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
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
            return LLMConfig(model=self.default_model)
        return config

    async def _chat_completion(
        self,
        messages: list[dict],
        config: LLMConfig,
        response_format: Optional[dict] = None,
    ) -> dict:
        model = config.model or self.default_model
        payload: dict = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
        }
        if config.max_tokens:
            payload["max_tokens"] = config.max_tokens
        if config.top_p is not None:
            payload["top_p"] = config.top_p
        if config.stop_sequences:
            payload["stop"] = config.stop_sequences
        if response_format:
            payload["response_format"] = response_format

        try:
            client = await self._get_client()
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Groq", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMError("Invalid Groq API key", code="LLM_AUTH_ERROR")
            if e.response.status_code == 429:
                raise LLMError("Groq rate limit exceeded", code="LLM_RATE_LIMIT")
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            raise LLMError(f"Groq request failed: {e.response.status_code}", code="LLM_HTTP_ERROR")

    async def _chat_completion_stream(
        self,
        messages: list[dict],
        config: LLMConfig,
    ) -> AsyncGenerator[str, None]:
        model = config.model or self.default_model
        payload: dict = {
            "model": model,
            "messages": messages,
            "temperature": config.temperature,
            "stream": True,
        }
        if config.max_tokens:
            payload["max_tokens"] = config.max_tokens

        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                        token = (
                            data.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if token:
                            yield token
                    except (json.JSONDecodeError, IndexError):
                        continue
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Groq", str(e))

    def _result_from_response(self, data: dict, model: str, generation_time: float) -> GenerationResult:
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

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        config = self._build_config(config)
        model = config.model or self.default_model
        start_time = time.time()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = await self._chat_completion(messages, config)
        return self._result_from_response(data, model, time.time() - start_time)

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
        messages = []
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        system_prompt = (
            f"Respond with valid JSON matching this schema:\n{schema_json}"
            + (f"\n\n{system}" if system else "")
        )
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = await self._chat_completion(
            messages, config, response_format={"type": "json_object"}
        )
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            parsed_data = json.loads(content)
            return output_schema.model_validate(parsed_data)
        except (json.JSONDecodeError, Exception) as e:
            raise LLMGenerationError(
                config.model or self.default_model,
                f"Structured output failed: {e}",
            )

    async def chat(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        config = self._build_config(config)
        model = config.model or self.default_model
        start_time = time.time()
        data = await self._chat_completion(
            [m.to_dict() for m in messages], config
        )
        return self._result_from_response(data, model, time.time() - start_time)

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        config = self._build_config(config)
        async for token in self._chat_completion_stream(
            [m.to_dict() for m in messages], config
        ):
            yield token

    async def count_tokens(self, text: str) -> int:
        from src.processing.chunker import count_tokens
        return count_tokens(text)

    async def list_models(self) -> list[str]:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ]

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False
