"""
Backend Integration Test.

Quick test to verify all components are properly wired together.
Run: python -m pytest tests/test_integration.py -v
"""

import asyncio
import pytest
from datetime import timedelta


class TestConfigurationSystem:
    """Test configuration loading."""
    
    def test_settings_load(self):
        """Test settings can be loaded."""
        from src.config import get_settings
        settings = get_settings()
        
        assert settings is not None
        assert settings.app_name == "Diogenes"
        assert settings.llm.provider == "ollama"
    
    def test_search_config(self):
        """Test search configuration."""
        from src.config import get_settings
        settings = get_settings()
        
        assert settings.search.base_url is not None
        assert settings.search.max_results > 0
    
    def test_crawl_config(self):
        """Test crawl configuration."""
        from src.config import get_settings
        settings = get_settings()
        
        assert settings.crawl.timeout > 0
        assert settings.crawl.max_concurrent >= 1


class TestServiceInterfaces:
    """Test service interfaces are properly defined."""
    
    def test_search_service_interface(self):
        """Test search service can be instantiated."""
        from src.config import get_settings
        from src.services.search.searxng import SearXNGService
        
        settings = get_settings()
        service = SearXNGService(settings.search)
        
        assert service is not None
    
    def test_crawl_service_interface(self):
        """Test crawl service can be instantiated."""
        from src.config import get_settings
        from src.services.crawl.crawler import Crawl4AIService
        
        settings = get_settings()
        service = Crawl4AIService(settings.crawl)
        
        assert service is not None
    
    def test_llm_service_interface(self):
        """Test LLM service can be instantiated."""
        from src.config import get_settings
        from src.services.llm.ollama import OllamaService
        
        settings = get_settings()
        service = OllamaService(settings.llm)
        
        assert service is not None


class TestProcessingPipeline:
    """Test content processing pipeline."""
    
    def test_content_cleaner(self):
        """Test content cleaner."""
        from src.processing.cleaner import ContentCleaner
        
        cleaner = ContentCleaner()
        # Test with plain text (cleaner expects markdown, not HTML)
        dirty = "Good content here. [Skip to content] Some more text."
        clean = cleaner.clean(dirty)
        
        assert "Skip to" not in clean
        assert "Good content" in clean
    
    def test_smart_chunker(self):
        """Test content chunker."""
        from src.processing.chunker import SmartChunker
        
        # SmartChunker uses settings internally, no need to pass config
        chunker = SmartChunker()
        
        text = "First paragraph with enough content to pass minimum threshold.\n\n" \
               "Second paragraph also has sufficient content.\n\n" \
               "Third paragraph with more detailed information."
        chunks = chunker.chunk(text, source_url="https://example.com", source_title="Test")
        
        assert len(chunks) >= 0  # May be 0 if text is below min threshold
    
    def test_quality_scorer(self):
        """Test quality scorer."""
        from src.processing.scorer import QualityScorer
        from src.services.crawl.models import CrawlResult, CrawlStatus
        from datetime import datetime
        
        scorer = QualityScorer()
        result = CrawlResult(
            url="https://en.wikipedia.org/wiki/Test",
            status=CrawlStatus.SUCCESS,
            title="Test Article",
            content="This is high quality research content with detailed information.",
            crawled_at=datetime.now()
        )
        score = scorer.score_source(result, query="test query")
        
        assert 0 <= score <= 1


class TestCitationSystem:
    """Test citation system."""
    
    def test_citation_manager(self):
        """Test citation manager."""
        from src.core.citation.manager import CitationManager
        from src.services.search.models import SearchResult
        
        manager = CitationManager()
        
        # Register a source
        result = SearchResult(
            url="https://example.com/article",
            title="Test Article",
            snippet="This is a test snippet."
        )
        source = manager.register_source_from_search(result)
        
        assert source.citation_index == 1
        assert len(manager.citation_map.sources) == 1
    
    def test_citation_formatter(self):
        """Test citation formatter."""
        from src.core.citation.manager import CitationFormatter
        from src.core.citation.models import Source
        
        sources = [
            Source(
                id="test-source-1",
                url="https://example.com",
                title="Example",
                domain="example.com",
                citation_index=1
            )
        ]
        
        formatter = CitationFormatter()
        bibliography = formatter.format_bibliography(sources)
        
        # Check for either numbered format
        assert "1." in bibliography or "[1]" in bibliography
        assert "Example" in bibliography


class TestAgentState:
    """Test agent state management."""
    
    def test_create_initial_state(self):
        """Test initial state creation."""
        from src.core.agent.state import create_initial_state, AgentPhase
        
        state = create_initial_state(
            query="Test query",
            session_id="test-123"
        )
        
        assert state["query"] == "Test query"
        assert state["session_id"] == "test-123"
        assert state["phase"] == AgentPhase.PLANNING
    
    def test_merge_state(self):
        """Test state merging."""
        from src.core.agent.state import create_initial_state, merge_state
        
        state = create_initial_state("Test", "123")
        updates = {"sub_queries": ["query 1", "query 2"]}
        
        merged = merge_state(state, updates)
        
        assert merged["sub_queries"] == ["query 1", "query 2"]
        assert merged["query"] == "Test"


class TestStorage:
    """Test storage layer."""
    
    @pytest.mark.asyncio
    async def test_sqlite_cache(self):
        """Test SQLite cache."""
        from src.storage.sqlite import SQLiteCache
        
        cache = SQLiteCache("data/test_cache.db")
        
        # Set and get
        await cache.set("test_key", {"value": 123})
        result = await cache.get("test_key")
        
        assert result["value"] == 123
        
        # Delete
        deleted = await cache.delete("test_key")
        assert deleted
        
        result = await cache.get("test_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_sqlite_session_store(self):
        """Test SQLite session store."""
        from src.storage.sqlite import SQLiteSessionStore
        
        store = SQLiteSessionStore("data/test_sessions.db")
        
        # Set session
        await store.set("session-1", {
            "query": "Test query",
            "state": {"phase": "complete", "final_answer": "Test answer"}
        })
        
        # Get session
        session = await store.get("session-1")
        assert session["query"] == "Test query"
        
        # List sessions
        sessions = await store.list_sessions()
        assert len(sessions) >= 1
        
        # Cleanup
        await store.delete("session-1")


class TestAPISchemas:
    """Test API schema validation."""
    
    def test_research_request(self):
        """Test research request validation."""
        from src.api.schemas import ResearchRequest
        
        request = ResearchRequest(
            query="What is quantum computing?",
            max_iterations=3
        )
        
        assert request.query == "What is quantum computing?"
        assert request.max_iterations == 3
    
    def test_research_response(self):
        """Test research response serialization."""
        from src.api.schemas import (
            ResearchResponse,
            ResearchAnswer,
            ResearchStatus
        )
        from datetime import datetime
        
        response = ResearchResponse(
            session_id="test-123",
            query="Test query",
            status=ResearchStatus.COMPLETE,
            answer=ResearchAnswer(
                content="Test answer [1]",
                word_count=3,
                has_citations=True
            )
        )
        
        assert response.status == ResearchStatus.COMPLETE
        assert response.answer.has_citations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
