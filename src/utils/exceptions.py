"""
Custom exceptions for Diogenes.

All application-specific exceptions inherit from DiogenesError.
"""

from typing import Optional


class DiogenesError(Exception):
    """Base exception for all Diogenes errors."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[str] = None,
        recoverable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.details = details
        self.recoverable = recoverable
    
    def to_dict(self, safe: bool = False) -> dict:
        """Convert exception to dictionary for API responses.
        
        Args:
            safe: If True, omit internal details (use in production).
        """
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
                "recoverable": self.recoverable,
            }
        }
        if not safe and self.details:
            result["error"]["details"] = self.details
        return result


# --- Search Errors ---

class SearchError(DiogenesError):
    """Errors related to search operations."""
    pass


class SearchTimeoutError(SearchError):
    """Search request timed out."""
    
    def __init__(self, query: str, timeout: float):
        super().__init__(
            message=f"Search timed out after {timeout}s",
            code="SEARCH_TIMEOUT",
            details=f"Query: {query}",
            recoverable=True,
        )


class SearchConnectionError(SearchError):
    """Cannot connect to search provider."""
    
    def __init__(self, provider: str, details: Optional[str] = None):
        super().__init__(
            message=f"Cannot connect to search provider: {provider}",
            code="SEARCH_CONNECTION_ERROR",
            details=details,
            recoverable=True,
        )


class NoSearchResultsError(SearchError):
    """No search results found."""
    
    def __init__(self, query: str):
        super().__init__(
            message="No search results found",
            code="NO_SEARCH_RESULTS",
            details=f"Query: {query}",
            recoverable=False,
        )


# --- Crawl Errors ---

class CrawlError(DiogenesError):
    """Errors related to web crawling."""
    pass


class CrawlTimeoutError(CrawlError):
    """Page crawl timed out."""
    
    def __init__(self, url: str, timeout: float):
        super().__init__(
            message=f"Crawl timed out after {timeout}s",
            code="CRAWL_TIMEOUT",
            details=f"URL: {url}",
            recoverable=True,
        )


class CrawlBlockedError(CrawlError):
    """Page blocked crawler access."""
    
    def __init__(self, url: str, status_code: Optional[int] = None):
        super().__init__(
            message="Access blocked by website",
            code="CRAWL_BLOCKED",
            details=f"URL: {url}, Status: {status_code}",
            recoverable=False,
        )


class CrawlContentError(CrawlError):
    """Error extracting content from page."""
    
    def __init__(self, url: str, reason: str):
        super().__init__(
            message=f"Failed to extract content: {reason}",
            code="CRAWL_CONTENT_ERROR",
            details=f"URL: {url}",
            recoverable=False,
        )


# --- LLM Errors ---

class LLMError(DiogenesError):
    """Errors related to LLM operations."""
    pass


class LLMTimeoutError(LLMError):
    """LLM inference timed out."""
    
    def __init__(self, model: str, timeout: float):
        super().__init__(
            message=f"LLM inference timed out after {timeout}s",
            code="LLM_TIMEOUT",
            details=f"Model: {model}",
            recoverable=True,
        )


class LLMConnectionError(LLMError):
    """Cannot connect to LLM provider."""
    
    def __init__(self, provider: str, details: Optional[str] = None):
        super().__init__(
            message=f"Cannot connect to LLM provider: {provider}",
            code="LLM_CONNECTION_ERROR",
            details=details,
            recoverable=True,
        )


class LLMModelNotFoundError(LLMError):
    """Requested model not available."""
    
    def __init__(self, model: str):
        super().__init__(
            message=f"Model not found: {model}",
            code="LLM_MODEL_NOT_FOUND",
            details="Please pull the model using 'ollama pull {model}'",
            recoverable=False,
        )


class LLMGenerationError(LLMError):
    """Error during text generation."""
    
    def __init__(self, model: str, reason: str):
        super().__init__(
            message=f"Generation failed: {reason}",
            code="LLM_GENERATION_ERROR",
            details=f"Model: {model}",
            recoverable=True,
        )


# --- Processing Errors ---

class ProcessingError(DiogenesError):
    """Errors related to content processing."""
    pass


class ChunkingError(ProcessingError):
    """Error during content chunking."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Chunking failed: {reason}",
            code="CHUNKING_ERROR",
            recoverable=False,
        )


class ExtractionError(ProcessingError):
    """Error during fact extraction."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Extraction failed: {reason}",
            code="EXTRACTION_ERROR",
            recoverable=True,
        )


# --- Agent Errors ---

class AgentError(DiogenesError):
    """Errors related to the research agent."""
    pass


class MaxIterationsError(AgentError):
    """Agent reached maximum iterations without sufficient coverage."""
    
    def __init__(self, iterations: int, coverage: float):
        super().__init__(
            message=f"Max iterations ({iterations}) reached with coverage {coverage:.0%}",
            code="MAX_ITERATIONS",
            details="The research may be incomplete",
            recoverable=False,
        )


class InsufficientSourcesError(AgentError):
    """Not enough sources to generate a reliable answer."""
    
    def __init__(self, found: int, required: int):
        super().__init__(
            message=f"Found {found} sources, need at least {required}",
            code="INSUFFICIENT_SOURCES",
            recoverable=False,
        )


# --- Session Errors ---

class SessionError(DiogenesError):
    """Errors related to session management."""
    pass


class SessionNotFoundError(SessionError):
    """Session not found."""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session not found: {session_id}",
            code="SESSION_NOT_FOUND",
            recoverable=False,
        )


class SessionExpiredError(SessionError):
    """Session has expired."""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session expired: {session_id}",
            code="SESSION_EXPIRED",
            recoverable=False,
        )


# --- Config Errors ---

class ConfigError(DiogenesError):
    """Errors related to configuration."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            details=details,
            recoverable=False,
        )


# --- Validation Errors ---

class ValidationError(DiogenesError):
    """Input validation errors."""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=f"Field: {field}",
            recoverable=False,
        )


class EmptyQueryError(ValidationError):
    """Query is empty or whitespace only."""
    
    def __init__(self):
        super().__init__(
            field="query",
            message="Query cannot be empty",
        )
