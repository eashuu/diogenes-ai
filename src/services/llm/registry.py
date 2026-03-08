"""
LLM Provider Registry — central factory for creating LLM service instances.

Usage::

    from src.services.llm.registry import get_llm_service

    # Uses the default provider from config
    service = get_llm_service()

    # Specify a provider
    service = get_llm_service("openai")

    # Specify provider + model
    service = get_llm_service("anthropic", model="claude-sonnet-4-20250514")
"""

from __future__ import annotations

from typing import Optional

from src.services.llm.base import LLMService
from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Cached provider instances keyed by (provider_name, model)
_provider_cache: dict[tuple[str, str | None], LLMService] = {}


def get_llm_service(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMService:
    """
    Create or return a cached LLM service instance.

    Args:
        provider: Provider name (ollama, openai, anthropic, groq, gemini).
                  Defaults to ``settings.llm.provider``.
        model: Default model for the service. Uses config defaults when None.

    Returns:
        An LLMService implementation.
    """
    settings = get_settings()

    if provider is None:
        provider = settings.llm.provider

    cache_key = (provider, model)
    if cache_key in _provider_cache:
        return _provider_cache[cache_key]

    service = _create_provider(provider, model, settings)
    _provider_cache[cache_key] = service
    return service


def _create_provider(provider: str, model: Optional[str], settings) -> LLMService:
    """Instantiate the correct provider."""
    llm_cfg = settings.llm
    providers_cfg = getattr(llm_cfg, "providers", None)

    if provider == "ollama":
        from src.services.llm.ollama import OllamaService

        return OllamaService(
            base_url=llm_cfg.base_url,
            default_model=model or llm_cfg.models.synthesizer,
            timeout=llm_cfg.timeout,
        )

    if provider == "openai":
        from src.services.llm.providers.openai import OpenAIProvider

        cfg = _provider_section(providers_cfg, "openai")
        return OpenAIProvider(
            api_key=cfg.get("api_key", ""),
            base_url=cfg.get("base_url", "https://api.openai.com/v1"),
            default_model=model or cfg.get("default_model", "gpt-4o-mini"),
            timeout=cfg.get("timeout", llm_cfg.timeout),
        )

    if provider == "anthropic":
        from src.services.llm.providers.anthropic import AnthropicProvider

        cfg = _provider_section(providers_cfg, "anthropic")
        return AnthropicProvider(
            api_key=cfg.get("api_key", ""),
            default_model=model or cfg.get("default_model", "claude-sonnet-4-20250514"),
            timeout=cfg.get("timeout", llm_cfg.timeout),
        )

    if provider == "groq":
        from src.services.llm.providers.groq import GroqProvider

        cfg = _provider_section(providers_cfg, "groq")
        return GroqProvider(
            api_key=cfg.get("api_key", ""),
            default_model=model or cfg.get("default_model", "llama-3.3-70b-versatile"),
            timeout=cfg.get("timeout", llm_cfg.timeout),
        )

    if provider == "gemini":
        from src.services.llm.providers.gemini import GeminiProvider

        cfg = _provider_section(providers_cfg, "gemini")
        return GeminiProvider(
            api_key=cfg.get("api_key", ""),
            default_model=model or cfg.get("default_model", "gemini-2.0-flash"),
            timeout=cfg.get("timeout", llm_cfg.timeout),
        )

    raise ValueError(f"Unknown LLM provider: {provider}")


def _provider_section(providers_cfg, name: str) -> dict:
    """Extract provider-specific config dict, falling back to env vars."""
    import os

    if providers_cfg and hasattr(providers_cfg, name):
        section = getattr(providers_cfg, name)
        if isinstance(section, dict):
            return section
        if hasattr(section, "model_dump"):
            return section.model_dump()

    # Fallback: read from environment variables
    prefix = f"DIOGENES_LLM_{name.upper()}_"
    env_cfg: dict = {}
    for key, val in os.environ.items():
        if key.startswith(prefix):
            cfg_key = key[len(prefix):].lower()
            env_cfg[cfg_key] = val
    return env_cfg


def list_available_providers() -> list[str]:
    """Return provider names that have API keys configured."""
    settings = get_settings()
    available = ["ollama"]  # Ollama doesn't need an API key

    for name in ("openai", "anthropic", "groq", "gemini"):
        providers_cfg = getattr(settings.llm, "providers", None)
        cfg = _provider_section(providers_cfg, name)
        if cfg.get("api_key"):
            available.append(name)

    return available


def clear_provider_cache() -> None:
    """Clear all cached provider instances."""
    _provider_cache.clear()
