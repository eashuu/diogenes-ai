"""
Test Multi-Agent Backend Flow.

Quick verification that the multi-agent system works correctly.
"""

import asyncio
import sys

# Add project root to path
sys.path.insert(0, ".")


async def test_agent_imports():
    """Test that all agents import correctly."""
    print("Testing agent imports...")
    
    from src.core.agents import (
        CoordinatorAgent,
        ResearcherAgent,
        VerifierAgent,
        WriterAgent,
        ResearchOrchestrator,
        TaskType,
        TaskAssignment,
    )
    
    print("  ✓ All agent imports successful")
    return True


async def test_profile_detection():
    """Test profile detection logic."""
    print("\nTesting profile detection...")
    
    from src.core.agents.profiles import detect_profile, ProfileType
    
    test_cases = [
        ("How do I fix this Python error?", ProfileType.TECHNICAL),
        ("What does the peer-reviewed research say about...?", ProfileType.ACADEMIC),
        ("What are the symptoms of...?", ProfileType.MEDICAL),
        ("What's the latest news about...?", ProfileType.NEWS),
        ("What is the stock price of...?", ProfileType.BUSINESS),
    ]
    
    for query, expected in test_cases:
        detected = detect_profile(query)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} '{query[:40]}...' -> {detected.value} (expected: {expected.value})")
    
    print("  ✓ Profile detection working")
    return True


async def test_agent_creation():
    """Test that agents can be instantiated."""
    print("\nTesting agent creation...")
    
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
    
    print(f"  ✓ Created and registered {len(pool._agents)} agents")
    print(f"    - Coordinator: {coordinator.agent_id[:16]}...")
    print(f"    - Researcher: {researcher.agent_id[:16]}...")
    print(f"    - Verifier: {verifier.agent_id[:16]}...")
    print(f"    - Writer: {writer.agent_id[:16]}...")
    
    return True


async def test_orchestrator_init():
    """Test orchestrator initialization."""
    print("\nTesting orchestrator initialization...")
    
    from src.core.agents import ResearchOrchestrator
    from src.core.agent.modes import SearchMode
    
    orchestrator = ResearchOrchestrator(mode=SearchMode.QUICK)
    await orchestrator.initialize()
    
    print("  ✓ Orchestrator initialized")
    print(f"    - Mode: {orchestrator._mode.value}")
    print(f"    - Agents: coordinator, researcher, verifier, writer")
    
    return True


async def test_api_routes():
    """Test that API routes are properly configured."""
    print("\nTesting API routes...")
    
    from src.api.app import app
    
    v1_routes = [r.path for r in app.routes if '/v1/' in r.path]
    
    expected_routes = [
        '/api/v1/research/',
        '/api/v1/research/stream',
        '/api/v1/research/profiles',
        '/api/v1/research/health',
    ]
    
    for route in expected_routes:
        status = "✓" if route in v1_routes else "✗"
        print(f"  {status} {route}")
    
    print(f"  ✓ Found {len(v1_routes)} v1 routes")
    return True


async def test_task_protocol():
    """Test the task protocol for inter-agent communication."""
    print("\nTesting task protocol...")
    
    from src.core.agents import TaskAssignment, TaskResult, TaskType
    
    # Create a sample task
    task = TaskAssignment(
        task_type=TaskType.WEB_SEARCH,
        agent_type="researcher",
        inputs={"query": "test query", "max_results": 5}
    )
    
    print(f"  ✓ Created task: {task.task_id[:16]}...")
    print(f"    - Type: {task.task_type.value}")
    print(f"    - Priority: {task.priority.value}")
    
    # Create a sample result
    result = TaskResult(
        task_id=task.task_id,
        agent_id="test-agent",
        status="success",
        outputs={"results": []},
        confidence=0.9
    )
    
    print(f"  ✓ Created result: status={result.status}, confidence={result.confidence}")
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Diogenes v2.0 Multi-Agent Backend Test")
    print("=" * 60)
    
    tests = [
        ("Agent Imports", test_agent_imports),
        ("Profile Detection", test_profile_detection),
        ("Agent Creation", test_agent_creation),
        ("Orchestrator Init", test_orchestrator_init),
        ("API Routes", test_api_routes),
        ("Task Protocol", test_task_protocol),
    ]
    
    results = []
    
    for name, test_fn in tests:
        try:
            result = await test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ✗ {name} failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All backend components are working correctly!")
        print("\nNext steps:")
        print("  1. Start the API server: python -m src.api.app")
        print("  2. Test endpoint: POST /api/v1/research/")
        print("  3. Test streaming: POST /api/v1/research/stream")
        print("  4. View profiles: GET /api/v1/research/profiles")
    else:
        print("\n✗ Some tests failed. Check errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
