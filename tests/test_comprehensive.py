"""
Comprehensive Backend Test Suite.

Tests all components and modes of the Diogenes v2.0 multi-agent system.
"""

import asyncio
import sys
import time
import traceback

sys.path.insert(0, ".")


class CheckResult:
    """Result holder for test checks (renamed from TestResult to avoid pytest collection warning)."""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.duration = 0.0
        self.details = {}


async def test_imports():
    """Test all critical imports work."""
    result = CheckResult("Imports")
    start = time.time()
    
    try:
        # Core agents
        from src.core.agents import (
            CoordinatorAgent,
            ResearcherAgent,
            VerifierAgent,
            WriterAgent,
            ResearchOrchestrator,
            AgentPool,
            TaskType,
            TaskAssignment,
        )
        
        # Processing
        from src.processing.chunker import SmartChunker
        from src.processing.cleaner import ContentCleaner
        from src.processing.scorer import QualityScorer
        from src.processing.models import ContentChunk
        
        # Services
        from src.services.search.searxng import SearXNGService
        from src.services.crawl.crawler import Crawl4AIService
        from src.services.llm.ollama import OllamaService
        
        # Config
        from src.config import get_settings
        
        # API
        from src.api.app import app
        
        result.passed = True
        result.details["modules"] = "All critical modules imported successfully"
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_config():
    """Test configuration loading."""
    result = CheckResult("Configuration")
    start = time.time()
    
    try:
        from src.config import clear_settings_cache, get_settings
        clear_settings_cache()
        settings = get_settings()
        
        # Check required settings
        assert settings.llm.base_url, "LLM base_url not set"
        assert settings.llm.models.synthesizer, "Synthesizer model not set"
        assert settings.search.base_url, "Search base_url not set"
        
        result.details["llm_model"] = settings.llm.models.synthesizer
        result.details["search_url"] = settings.search.base_url
        result.details["environment"] = settings.environment
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
    
    result.duration = time.time() - start
    return result


async def test_ollama_connection():
    """Test Ollama service connection."""
    result = CheckResult("Ollama Connection")
    start = time.time()
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                result.details["available_models"] = len(models)
                result.details["has_gpt_oss"] = any("gpt-oss" in m for m in models)
                result.passed = True
            else:
                result.error = f"Ollama returned status {resp.status_code}"
                
    except Exception as e:
        result.error = f"Cannot connect to Ollama: {e}"
    
    result.duration = time.time() - start
    return result


async def test_searxng_connection():
    """Test SearXNG service connection."""
    result = CheckResult("SearXNG Connection")
    start = time.time()
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8080/healthz", timeout=5)
            
            if resp.status_code == 200:
                result.passed = True
                result.details["status"] = "healthy"
            else:
                # Try search endpoint
                resp = await client.get("http://localhost:8080/search?q=test&format=json", timeout=10)
                if resp.status_code == 200:
                    result.passed = True
                    result.details["status"] = "healthy (via search)"
                else:
                    result.error = f"SearXNG returned status {resp.status_code}"
                    
    except Exception as e:
        result.error = f"Cannot connect to SearXNG: {e}"
    
    result.duration = time.time() - start
    return result


async def test_processing_pipeline():
    """Test content processing pipeline."""
    result = CheckResult("Processing Pipeline")
    start = time.time()
    
    try:
        from src.processing.chunker import SmartChunker
        from src.processing.cleaner import ContentCleaner
        from src.processing.scorer import QualityScorer
        from src.services.crawl.models import CrawlResult
        from datetime import datetime
        
        # Test cleaner with markdown content (what crawl4ai returns)
        cleaner = ContentCleaner()
        # Content cleaner receives markdown, not raw HTML
        dirty_content = """# Test Page

Hello World this is the main content of the page.

[Skip to content]
[Menu]
Cookie Policy: We use cookies...

This is meaningful content that should be preserved in the output.

Share on Facebook   Tweet   
Advertisement
ADVERTISEMENT

More meaningful content here that is long enough to pass the filter.

© 2024 All Rights Reserved.

   
   Extra    spaces   here   with   noise.
"""
        cleaned = cleaner.clean(dirty_content)
        assert "Hello World" in cleaned, "Main content lost"
        assert "meaningful content" in cleaned, "Meaningful content lost"
        # Check that boilerplate is removed
        assert "Cookie Policy" not in cleaned or "cookies" not in cleaned, "Cookie notice not fully removed"
        result.details["cleaner"] = "OK"
        
        # Test chunker
        chunker = SmartChunker(chunk_size=100, chunk_overlap=20)
        long_content = "This is a test sentence. " * 100
        chunks = chunker.chunk(
            content=long_content,
            source_url="https://example.com",
            source_title="Test"
        )
        assert len(chunks) > 1, "Content not chunked"
        assert all(hasattr(c, 'content') for c in chunks), "Chunks missing content attribute"
        result.details["chunker"] = f"OK ({len(chunks)} chunks)"
        
        # Test scorer
        scorer = QualityScorer()
        
        # Test domain scoring
        domain_score = scorer.score_domain("https://arxiv.org/paper")
        assert domain_score > 0.8, "arxiv should have high authority"
        result.details["scorer_domain"] = f"OK (arxiv={domain_score:.2f})"
        
        # Test source scoring with CrawlResult
        from src.services.crawl.models import CrawlStatus
        mock_crawl = CrawlResult(
            url="https://example.com/test",
            status=CrawlStatus.SUCCESS,
            title="Test Page",
            content="This is test content about quantum physics and research.",
            crawled_at=datetime.now()
        )
        source_score = scorer.score_source(mock_crawl, query="quantum physics")
        assert 0 <= source_score <= 1, "Score out of range"
        result.details["scorer_source"] = f"OK (score={source_score:.2f})"
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_agent_creation():
    """Test agent instantiation."""
    result = CheckResult("Agent Creation")
    start = time.time()
    
    try:
        from src.core.agents import (
            CoordinatorAgent,
            ResearcherAgent,
            VerifierAgent,
            WriterAgent,
            AgentPool,
        )
        
        pool = AgentPool()
        
        coordinator = CoordinatorAgent()
        researcher = ResearcherAgent()
        verifier = VerifierAgent()
        writer = WriterAgent()
        
        pool.register(coordinator)
        pool.register(researcher)
        pool.register(verifier)
        pool.register(writer)
        
        result.details["agents_registered"] = len(pool._agents)
        result.details["coordinator_id"] = coordinator.agent_id[:20]
        result.details["researcher_id"] = researcher.agent_id[:20]
        
        # Test pool retrieval
        retrieved = pool.get_agent("researcher")
        assert retrieved is not None, "Could not retrieve researcher"
        assert retrieved.agent_id == researcher.agent_id, "Wrong agent retrieved"
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_verifier_agent():
    """Test verifier agent functionality."""
    result = CheckResult("Verifier Agent")
    start = time.time()
    
    try:
        from src.core.agents import VerifierAgent, TaskAssignment, TaskType
        
        verifier = VerifierAgent()
        
        claims = [
            {"text": "The speed of light is approximately 300,000 km/s."},
            {"text": "Water freezes at 0 degrees Celsius."},
        ]
        
        sources = [
            {
                "url": "https://physics.info",
                "title": "Physics Facts",
                "content": "The speed of light in vacuum is approximately 299,792 km/s, often rounded to 300,000 km/s."
            },
            {
                "url": "https://science.edu",
                "title": "Science Education",
                "content": "Water freezes at 0°C (32°F) at standard atmospheric pressure."
            }
        ]
        
        task = TaskAssignment(
            task_type=TaskType.VERIFY_CLAIMS,
            agent_type="verifier",
            inputs={"claims": claims, "sources": sources}
        )
        
        task_result = await verifier.execute(task)
        
        assert task_result.status == "success", f"Task failed: {task_result.errors}"
        assert "verified_claims" in task_result.outputs, "Missing verified_claims"
        assert "reliability_score" in task_result.outputs, "Missing reliability_score"
        
        result.details["claims_verified"] = len(task_result.outputs.get("verified_claims", []))
        result.details["reliability_score"] = task_result.outputs.get("reliability_score", 0)
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_writer_agent():
    """Test writer agent functionality."""
    result = CheckResult("Writer Agent")
    start = time.time()
    
    try:
        from src.core.agents import WriterAgent
        
        writer = WriterAgent()
        
        findings = [
            {"content": "Python is a high-level programming language.", "url": "https://python.org"},
            {"content": "Python was created by Guido van Rossum.", "url": "https://wiki.python.org"},
        ]
        
        sources = [
            {"url": "https://python.org", "title": "Python.org"},
            {"url": "https://wiki.python.org", "title": "Python Wiki"},
        ]
        
        synthesis = await writer.synthesize_research(
            query="What is Python?",
            findings=findings,
            sources=sources,
            style="brief"
        )
        
        assert "content" in synthesis, "Missing content"
        content = synthesis.get("content", "")
        assert len(content) > 50, "Content too short"
        
        result.details["word_count"] = synthesis.get("word_count", 0)
        result.details["citation_count"] = synthesis.get("citation_count", 0)
        result.details["preview"] = content[:100] + "..."
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_orchestrator_init():
    """Test orchestrator initialization."""
    result = CheckResult("Orchestrator Init")
    start = time.time()
    
    try:
        from src.core.agents import ResearchOrchestrator
        from src.core.agent.modes import SearchMode
        
        orchestrator = ResearchOrchestrator(mode=SearchMode.QUICK)
        await orchestrator.initialize()
        
        assert orchestrator._coordinator is not None, "Coordinator not initialized"
        assert orchestrator._researcher is not None, "Researcher not initialized"
        assert orchestrator._verifier is not None, "Verifier not initialized"
        assert orchestrator._writer is not None, "Writer not initialized"
        
        result.details["mode"] = orchestrator._mode.value
        result.details["agents_ready"] = 4
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_research_modes():
    """Test all research modes are configured correctly."""
    result = CheckResult("Research Modes")
    start = time.time()
    
    try:
        from src.core.agent.modes import SearchMode, MODE_CONFIGS
        
        modes_info = {}
        for mode in SearchMode:
            config = MODE_CONFIGS[mode]
            modes_info[mode.value] = {
                "max_search": config.max_search_results,
                "max_crawl": config.max_sources_to_crawl,
                "max_iterations": config.max_iterations,
            }
        
        assert len(modes_info) >= 5, "Missing modes"
        assert "quick" in modes_info, "Missing quick mode"
        assert "balanced" in modes_info, "Missing balanced mode"
        assert "deep" in modes_info, "Missing deep mode"
        
        result.details["modes"] = modes_info
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_research_profiles():
    """Test research profiles."""
    result = CheckResult("Research Profiles")
    start = time.time()
    
    try:
        from src.core.agents.profiles import (
            ProfileType,
            PROFILES,
            get_profile,
            detect_profile,
        )
        
        # Check all profiles exist
        profile_names = [p.value for p in ProfileType]
        result.details["profiles"] = profile_names
        
        # Test profile detection
        test_cases = [
            ("How do I fix this Python bug?", "technical"),
            ("What does peer-reviewed research say?", "academic"),
            ("What are the symptoms of flu?", "medical"),
            ("Latest news about elections", "news"),
        ]
        
        detection_results = []
        for query, expected in test_cases:
            detected = detect_profile(query).value
            detection_results.append(f"{expected}: {'✓' if detected == expected else '✗'}")
        
        result.details["detection_tests"] = detection_results
        
        # Test profile retrieval
        academic = get_profile(ProfileType.ACADEMIC)
        assert academic.name == "Academic Research", "Wrong profile name"
        assert academic.verification.strict_mode, "Academic should have strict mode"
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_api_routes():
    """Test API routes are configured."""
    result = CheckResult("API Routes")
    start = time.time()
    
    try:
        from src.api.app import app
        
        routes = {r.path: r.methods for r in app.routes if hasattr(r, 'methods')}
        
        # Check v1 routes
        v1_routes = [p for p in routes if '/v1/' in p]
        
        result.details["v1_routes"] = len(v1_routes)
        result.details["v1_endpoints"] = v1_routes
        
        assert len(v1_routes) >= 3, "Missing v1 routes"
        assert any('research' in r for r in v1_routes), "Missing v1 research route"
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def test_full_research_flow():
    """Test a complete research flow (quick mode)."""
    result = CheckResult("Full Research Flow")
    start = time.time()
    
    try:
        from src.core.agents import ResearchOrchestrator
        from src.core.agent.modes import SearchMode
        
        # Use QUICK mode for faster testing
        orchestrator = ResearchOrchestrator(mode=SearchMode.QUICK)
        await orchestrator.initialize()
        
        query = "What is the capital of France?"
        
        # Run research with streaming
        events = []
        async for event in orchestrator.research_stream(query=query, style="brief"):
            events.append(event.get("type"))
            
            if event.get("type") == "complete":
                data = event.get("data", {})
                result.details["answer_length"] = len(data.get("answer", ""))
                result.details["sources_found"] = len(data.get("sources", []))
                result.details["reliability_score"] = data.get("reliability_score", 0)
                result.details["duration"] = data.get("duration_seconds", 0)
                
            elif event.get("type") == "error":
                raise Exception(event.get("data", {}).get("error", "Unknown error"))
        
        result.details["event_types"] = list(set(events))
        
        # Verify we got a complete event
        assert "complete" in events, "No complete event received"
        assert result.details.get("answer_length", 0) > 0, "No answer generated"
        
        result.passed = True
        
    except Exception as e:
        result.error = str(e)
        result.details["traceback"] = traceback.format_exc()
    
    result.duration = time.time() - start
    return result


async def main():
    """Run all tests."""
    print("=" * 70)
    print("Diogenes v2.0 Comprehensive Backend Test Suite")
    print("=" * 70)
    print()
    
    # Define test order (basic to complex)
    tests = [
        ("1. Imports", test_imports),
        ("2. Configuration", test_config),
        ("3. Ollama Connection", test_ollama_connection),
        ("4. SearXNG Connection", test_searxng_connection),
        ("5. Processing Pipeline", test_processing_pipeline),
        ("6. Agent Creation", test_agent_creation),
        ("7. Research Modes", test_research_modes),
        ("8. Research Profiles", test_research_profiles),
        ("9. API Routes", test_api_routes),
        ("10. Verifier Agent", test_verifier_agent),
        ("11. Writer Agent", test_writer_agent),
        ("12. Orchestrator Init", test_orchestrator_init),
        ("13. Full Research Flow", test_full_research_flow),
    ]
    
    results = []
    
    for name, test_fn in tests:
        print(f"\n{'-' * 50}")
        print(f"Running: {name}")
        print(f"{'-' * 50}")
        
        try:
            result = await test_fn()
            results.append(result)
            
            if result.passed:
                print(f"  ✓ PASSED ({result.duration:.2f}s)")
            else:
                print(f"  ✗ FAILED ({result.duration:.2f}s)")
                if result.error:
                    print(f"    Error: {result.error}")
            
            # Print details
            for key, value in result.details.items():
                if isinstance(value, dict):
                    print(f"    {key}:")
                    for k, v in value.items():
                        print(f"      {k}: {v}")
                elif isinstance(value, list):
                    print(f"    {key}: {', '.join(str(v) for v in value[:5])}")
                else:
                    val_str = str(value)
                    if len(val_str) > 60:
                        val_str = val_str[:60] + "..."
                    print(f"    {key}: {val_str}")
                    
        except Exception as e:
            print(f"  ✗ CRASHED: {e}")
            result = CheckResult(name)
            result.error = str(e)
            results.append(result)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    for r in results:
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"  {status}: {r.name} ({r.duration:.2f}s)")
    
    print(f"\nTotal: {passed}/{len(results)} passed, {failed} failed")
    
    total_time = sum(r.duration for r in results)
    print(f"Total time: {total_time:.1f}s")
    
    if failed == 0:
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("✗ SOME TESTS FAILED - Review errors above")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
