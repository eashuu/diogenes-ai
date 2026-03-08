"""
Diogenes Configuration System

Hierarchical configuration with environment variable overrides.
Uses Pydantic Settings for type validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional, Literal
import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class SearchConfig(BaseSettings):
    """Search service configuration."""
    
    provider: Literal["searxng"] = "searxng"
    base_url: str = "http://localhost:8080"
    timeout: float = 20.0
    max_results: int = 10
    cache_ttl: int = 3600  # 1 hour
    categories: list[str] = Field(default_factory=lambda: ["general", "science", "it"])
    language: str = "en-US"
    verify_ssl: bool = True  # Set False for self-signed certs
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_SEARCH_")


class CrawlConfig(BaseSettings):
    """Crawl service configuration."""
    
    provider: Literal["crawl4ai"] = "crawl4ai"
    max_concurrent: int = 5
    timeout: float = 30.0
    max_content_length: int = 500000  # 500KB
    rate_limit_per_domain: float = 1.0  # seconds between requests to same domain
    cache_ttl: int = 86400  # 24 hours
    user_agent: str = "DiogenesResearchBot/2.0"
    max_urls_per_request: int = 50  # Hard cap on URLs per batch crawl
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_CRAWL_")


class LLMModelsConfig(BaseSettings):
    """LLM model configuration."""
    
    planner: str = "qwen3:8b"  # Fast model for query decomposition
    extractor: str = "qwen3:8b"  # Fast model for fact extraction
    synthesizer: str = "qwen3:8b"  # Quality model for final answer
    reflector: str = "qwen3:8b"  # Quality model for reflection
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_LLM_MODEL_")


class LLMProviderConfig(BaseSettings):
    """Per-provider configuration (API key, base URL, default model)."""
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    timeout: Optional[float] = None

    model_config = SettingsConfigDict(extra="allow")


class LLMProvidersConfig(BaseSettings):
    """Container for all provider-specific configs."""
    openai: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
    anthropic: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
    groq: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
    gemini: LLMProviderConfig = Field(default_factory=LLMProviderConfig)

    model_config = SettingsConfigDict(env_prefix="DIOGENES_LLM_PROVIDERS_")


class LLMConfig(BaseSettings):
    """LLM service configuration."""
    
    provider: Literal["ollama", "openai", "anthropic", "groq", "gemini"] = "ollama"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: float = 120.0
    verify_ssl: bool = True  # Set False for self-signed certs
    models: LLMModelsConfig = Field(default_factory=LLMModelsConfig)
    providers: LLMProvidersConfig = Field(default_factory=LLMProvidersConfig)
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_LLM_")


class ProcessingConfig(BaseSettings):
    """Content processing configuration."""
    
    chunk_size: int = 512  # Target tokens per chunk
    chunk_overlap: int = 64  # Overlap tokens
    min_chunk_size: int = 100  # Minimum tokens
    max_chunks_per_source: int = 20
    max_total_context: int = 32000  # Max tokens for context
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_PROCESSING_")


class CacheConfig(BaseSettings):
    """Cache configuration."""
    
    provider: Literal["sqlite", "memory"] = "sqlite"
    database: str = "data/cache.db"
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_CACHE_")


class SessionConfig(BaseSettings):
    """Session storage configuration."""
    
    provider: Literal["sqlite", "memory"] = "sqlite"
    database: str = "data/sessions.db"
    ttl: int = 86400  # 24 hours
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_SESSION_")


class MemoryConfig(BaseSettings):
    """Memory store configuration."""
    
    database: str = "data/memories.db"
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_MEMORY_")


class ConversationConfig(BaseSettings):
    """Conversation tree storage configuration."""
    
    database: str = "data/conversations.db"
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_CONVERSATION_")


class AgentConfig(BaseSettings):
    """Agent behavior configuration."""
    
    max_iterations: int = 3  # Max search-reflect loops
    min_sources: int = 3  # Minimum sources before synthesis
    max_sources: int = 8  # Maximum sources to crawl
    coverage_threshold: float = 0.7  # Min coverage score to proceed
    enable_memory_context: bool = True  # Inject user memories into research prompts
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_AGENT_")


class APIConfig(BaseSettings):
    """API server configuration."""
    
    host: str = "127.0.0.1"  # Localhost-only by default (FOSS-local-first)
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    debug: bool = False
    require_api_key: bool = False  # Enable to require X-API-Key header
    api_key: str = ""  # API key value when require_api_key is True
    max_concurrent_research: int = 2  # Max simultaneous research sessions
    workers: int = 1  # Uvicorn workers (auto-scales in production if 0)
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_API_")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    json_format: bool = False  # Enable JSON-structured log output (recommended for production)
    file: Optional[str] = None  # Optional log file path
    
    model_config = SettingsConfigDict(env_prefix="DIOGENES_LOG_")


class Settings(BaseSettings):
    """
    Main application settings.
    
    Configuration priority (highest to lowest):
    1. Environment variables (DIOGENES_*)
    2. .env file
    3. Config YAML file
    4. Default values
    """
    
    app_name: str = "Diogenes"
    version: str = "2.0.0"
    environment: Literal["development", "production", "test"] = "development"
    
    # Sub-configurations
    search: SearchConfig = Field(default_factory=SearchConfig)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    model_config = SettingsConfigDict(
        env_prefix="DIOGENES_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        """Load settings from a YAML file."""
        if not path.exists():
            return cls()
        
        with open(path, "r") as f:
            config_data = yaml.safe_load(f) or {}
        
        return cls(**config_data)


def load_config(config_path: Optional[str] = None) -> Settings:
    """
    Load configuration with proper precedence.
    
    Args:
        config_path: Optional path to YAML config file.
                    If not provided, checks CONFIG_PATH env var,
                    then falls back to config/default.yaml
    """
    # Determine config file path
    if config_path is None:
        config_path = os.environ.get("DIOGENES_CONFIG_PATH")
    
    if config_path is None:
        # Load default.yaml first, then layer environment-specific config on top
        env = os.environ.get("DIOGENES_ENVIRONMENT", "development")
        default_path = Path("config/default.yaml")
        env_path = Path(f"config/{env}.yaml")

        # Start with defaults from YAML
        merged: dict = {}
        if default_path.exists():
            with open(default_path, "r") as f:
                merged = yaml.safe_load(f) or {}

        # Layer environment-specific overrides
        if env_path.exists():
            with open(env_path, "r") as f:
                env_data = yaml.safe_load(f) or {}
            merged = _deep_merge(merged, env_data)

        # Remove YAML values that have env var overrides set
        # so Pydantic Settings can pick up env vars with higher precedence
        merged = _strip_env_overrides(merged)
        return Settings(**merged) if merged else Settings()

    # Load from explicit path
    if config_path and Path(config_path).exists():
        settings = Settings.from_yaml(Path(config_path))
    else:
        settings = Settings()

    return settings


# Mapping of YAML paths to env var names
_ENV_VAR_MAP = {
    ("search", "base_url"): "DIOGENES_SEARCH_BASE_URL",
    ("llm", "base_url"): "DIOGENES_LLM_BASE_URL",
    ("llm", "provider"): "DIOGENES_LLM_PROVIDER",
    ("api", "host"): "DIOGENES_API_HOST",
    ("api", "port"): "DIOGENES_API_PORT",
    ("api", "cors_origins"): "DIOGENES_API_CORS_ORIGINS",
}


def _strip_env_overrides(data: dict) -> dict:
    """Remove YAML values that have env var overrides set."""
    result = dict(data)
    for path, env_var in _ENV_VAR_MAP.items():
        if os.environ.get(env_var) is not None:
            # Walk the path and remove the leaf
            d = result
            for key in path[:-1]:
                if key not in d or not isinstance(d[key], dict):
                    break
                d = d[key]
            else:
                d.pop(path[-1], None)
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Use this as the primary way to access settings throughout the app.
    The settings are cached after first load.  When runtime overrides
    are applied via :func:`apply_runtime_overrides`, the cache is
    automatically invalidated so the next call returns fresh settings.
    """
    settings = load_config()

    # Layer on any runtime overrides
    if _runtime_overrides:
        settings = _apply_overrides(settings, _runtime_overrides)

    return settings


# ---------------------------------------------------------------------------
# Runtime override support
# ---------------------------------------------------------------------------

_runtime_overrides: dict = {}


def apply_runtime_overrides(section: str, updates: dict) -> None:
    """Apply runtime config overrides and invalidate the settings cache.

    Args:
        section: Top-level config key, e.g. ``"llm"``, ``"search"``.
        updates: Dict of field → value overrides for that section.
                 Nested dicts (e.g. ``{"models": {"planner": "phi3:mini"}}``)
                 are merged one level deep.
    """
    if section not in _runtime_overrides:
        _runtime_overrides[section] = {}
    _runtime_overrides[section].update(updates)
    get_settings.cache_clear()


def _apply_overrides(settings: Settings, overrides: dict) -> Settings:
    """Return a copy of *settings* with *overrides* applied."""
    top_updates: dict = {}
    for section, values in overrides.items():
        sub_config = getattr(settings, section, None)
        if sub_config is None or not hasattr(sub_config, "model_copy"):
            continue
        # Handle nested sub-configs (e.g. llm.models)
        clean_values: dict = {}
        for k, v in values.items():
            if isinstance(v, dict):
                nested = getattr(sub_config, k, None)
                if nested and hasattr(nested, "model_copy"):
                    clean_values[k] = nested.model_copy(update=v)
                else:
                    clean_values[k] = v
            else:
                clean_values[k] = v
        top_updates[section] = sub_config.model_copy(update=clean_values)
    if top_updates:
        return settings.model_copy(update=top_updates)
    return settings


# Convenience function to clear cache (useful for testing)
def clear_settings_cache():
    """Clear the settings cache and runtime overrides."""
    _runtime_overrides.clear()
    get_settings.cache_clear()
