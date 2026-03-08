"""
Google Gemini LLM provider implementation.
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


class GeminiProvider(LLMService):
    """
    Google Gemini LLM provider using the REST API (v1beta).
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-2.0-flash",
        timeout: float = 120.0,
    ):
        if not api_key:
            raise ValueError("Google API key is required")
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.default_model = default_model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
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

    def _build_generation_config(self, config: LLMConfig) -> dict:
        gen_config: dict = {"temperature": config.temperature}
        if config.max_tokens:
            gen_config["maxOutputTokens"] = config.max_tokens
        if config.top_p is not None:
            gen_config["topP"] = config.top_p
        if config.top_k is not None:
            gen_config["topK"] = config.top_k
        if config.stop_sequences:
            gen_config["stopSequences"] = config.stop_sequences
        return gen_config

    def _model_url(self, model: str, action: str) -> str:
        return f"{self.base_url}/models/{model}:{action}?key={self.api_key}"

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        config = self._build_config(config)
        model = config.model or self.default_model
        start_time = time.time()

        payload: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": self._build_generation_config(config),
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        try:
            client = await self._get_client()
            response = await client.post(self._model_url(model, "generateContent"), json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Gemini", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            if e.response.status_code in (401, 403):
                raise LLMError("Invalid Google API key", code="LLM_AUTH_ERROR")
            if e.response.status_code == 429:
                raise LLMError("Google API rate limit exceeded", code="LLM_RATE_LIMIT")
            raise LLMError(f"Gemini request failed: {e.response.status_code}", code="LLM_HTTP_ERROR")

        generation_time = time.time() - start_time
        candidates = data.get("candidates", [])
        content = ""
        finish_reason = None
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)
            finish_reason = candidates[0].get("finishReason")

        usage_meta = data.get("usageMetadata", {})
        usage = TokenUsage(
            prompt_tokens=usage_meta.get("promptTokenCount", 0),
            completion_tokens=usage_meta.get("candidatesTokenCount", 0),
            total_tokens=usage_meta.get("totalTokenCount", 0),
        )

        return GenerationResult(
            content=content,
            model=model,
            usage=usage,
            generation_time=generation_time,
            finish_reason=finish_reason,
        )

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        config = self._build_config(config)
        model = config.model or self.default_model

        payload: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": self._build_generation_config(config),
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        try:
            client = await self._get_client()
            async with client.stream(
                "POST", self._model_url(model, "streamGenerateContent") + "&alt=sse", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Gemini", str(e))

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> T:
        config = self._build_config(config)
        model = config.model or self.default_model
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)

        payload: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                **self._build_generation_config(config),
                "responseMimeType": "application/json",
            },
        }
        system_text = (
            f"Respond with valid JSON matching this schema:\n{schema_json}"
            + (f"\n\n{system}" if system else "")
        )
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        try:
            client = await self._get_client()
            response = await client.post(self._model_url(model, "generateContent"), json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Gemini structured request failed: {e.response.status_code}", code="LLM_HTTP_ERROR")

        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        try:
            parsed_data = json.loads(content)
            return output_schema.model_validate(parsed_data)
        except (json.JSONDecodeError, Exception) as e:
            raise LLMGenerationError(model, f"Structured output failed: {e}")

    async def chat(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> GenerationResult:
        config = self._build_config(config)
        model = config.model or self.default_model
        start_time = time.time()

        # Map to Gemini format: system instruction separate, user/model roles
        system_text = None
        gemini_contents = []
        for m in messages:
            if m.role.value == "system":
                system_text = m.content
            else:
                role = "model" if m.role.value == "assistant" else "user"
                gemini_contents.append({"role": role, "parts": [{"text": m.content}]})

        payload: dict = {
            "contents": gemini_contents,
            "generationConfig": self._build_generation_config(config),
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        try:
            client = await self._get_client()
            response = await client.post(self._model_url(model, "generateContent"), json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Gemini", str(e))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMModelNotFoundError(model)
            raise LLMError(f"Gemini chat failed: {e.response.status_code}", code="LLM_HTTP_ERROR")

        generation_time = time.time() - start_time
        candidates = data.get("candidates", [])
        content = ""
        finish_reason = None
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)
            finish_reason = candidates[0].get("finishReason")

        usage_meta = data.get("usageMetadata", {})
        usage = TokenUsage(
            prompt_tokens=usage_meta.get("promptTokenCount", 0),
            completion_tokens=usage_meta.get("candidatesTokenCount", 0),
            total_tokens=usage_meta.get("totalTokenCount", 0),
        )

        return GenerationResult(
            content=content, model=model, usage=usage, generation_time=generation_time,
            finish_reason=finish_reason,
        )

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[str, None]:
        config = self._build_config(config)
        model = config.model or self.default_model

        system_text = None
        gemini_contents = []
        for m in messages:
            if m.role.value == "system":
                system_text = m.content
            else:
                role = "model" if m.role.value == "assistant" else "user"
                gemini_contents.append({"role": role, "parts": [{"text": m.content}]})

        payload: dict = {
            "contents": gemini_contents,
            "generationConfig": self._build_generation_config(config),
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        try:
            client = await self._get_client()
            async with client.stream(
                "POST", self._model_url(model, "streamGenerateContent") + "&alt=sse", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException:
            raise LLMTimeoutError(model, self.timeout)
        except httpx.ConnectError as e:
            raise LLMConnectionError("Gemini", str(e))

    async def count_tokens(self, text: str) -> int:
        try:
            client = await self._get_client()
            model = self.default_model
            response = await client.post(
                self._model_url(model, "countTokens"),
                json={"contents": [{"parts": [{"text": text}]}]},
            )
            if response.status_code == 200:
                return response.json().get("totalTokens", len(text) // 4)
        except Exception:
            pass
        return len(text) // 4

    async def list_models(self) -> list[str]:
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/models?key={self.api_key}"
            )
            response.raise_for_status()
            data = response.json()
            return [
                m["name"].replace("models/", "")
                for m in data.get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
        except Exception:
            return ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"]

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/models?key={self.api_key}"
            )
            return response.status_code == 200
        except Exception:
            return False
