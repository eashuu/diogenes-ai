"""
Live Test - Multi-Agent Research with gpt-oss:20b.

Runs an actual research query through the v2.0 multi-agent system.
"""

import asyncio
import sys
import time

sys.path.insert(0, ".")


async def test_live_research():
    """Run a live research query through the multi-agent system."""
    from src.core.agents import ResearchOrchestrator, ResearchPhase
    from src.core.agent.modes import SearchMode
    from src.config import get_settings
    
    settings = get_settings()
    print("=" * 70)
    print("Diogenes v2.0 - Live Multi-Agent Research Test")
    print("=" * 70)
    print(f"LLM Provider: {settings.llm.provider}")
    print(f"LLM Base URL: {settings.llm.base_url}")
    print(f"Synthesizer Model: {settings.llm.models.synthesizer}")
    print(f"Planner Model: {settings.llm.models.planner}")
    print("=" * 70)
    
    # Create orchestrator in QUICK mode for faster testing
    orchestrator = ResearchOrchestrator(mode=SearchMode.QUICK)
    
    print("\n[1/5] Initializing agents...")
    await orchestrator.initialize()
    print("  ✓ Agents initialized")
    
    # Test query
    query = "What is quantum entanglement and how does it work?"
    print(f"\n[2/5] Research Query: '{query}'")
    
    print("\n[3/5] Running multi-agent research (streaming)...")
    print("-" * 70)
    
    start_time = time.time()
    sources_found = 0
    answer_chunks = []
    final_result = None
    
    try:
        async for event in orchestrator.research_stream(
            query=query,
            style="comprehensive"
        ):
            event_type = event.get("type")
            data = event.get("data", {})
            
            if event_type == "progress":
                phase = data.get("phase", "")
                progress = data.get("progress_pct", 0) * 100
                msg = data.get("messages", [""])[0] if data.get("messages") else ""
                sources = data.get("sources_found", 0)
                if sources > sources_found:
                    sources_found = sources
                print(f"  [{progress:5.1f}%] {phase:15} | {msg[:50]}")
            
            elif event_type == "source":
                url = data.get("url", "")
                title = data.get("title", "")
                print(f"  [SOURCE] {title[:40]}... ({url[:30]}...)")
            
            elif event_type == "answer_chunk":
                chunk = data.get("content", "")
                answer_chunks.append(chunk)
                # Print dots to show progress
                print(".", end="", flush=True)
            
            elif event_type == "complete":
                final_result = data
                print("\n")  # New line after answer chunks
                
            elif event_type == "error":
                print(f"\n  [ERROR] {data.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"\n  [ERROR] Research failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    elapsed = time.time() - start_time
    
    print("-" * 70)
    print(f"\n[4/5] Research Complete in {elapsed:.1f}s")
    
    if final_result:
        print("\n[5/5] Results Summary:")
        print("-" * 70)
        
        answer = final_result.get("answer", "")
        if answer:
            # Print first 500 chars of answer
            print("\n📝 ANSWER (preview):")
            print(answer[:800] + ("..." if len(answer) > 800 else ""))
        
        print(f"\n📊 METRICS:")
        print(f"  - Sources Found: {len(final_result.get('sources', []))}")
        print(f"  - Reliability Score: {final_result.get('reliability_score', 0):.2f}")
        print(f"  - Confidence: {final_result.get('confidence', 0):.2f}")
        print(f"  - Iterations: {final_result.get('iterations', 0)}")
        print(f"  - Duration: {final_result.get('duration_seconds', 0):.1f}s")
        
        # Print sources
        sources = final_result.get("sources", [])
        if sources:
            print(f"\n📚 SOURCES ({len(sources)} total):")
            for i, src in enumerate(sources[:5], 1):
                title = src.get("title", "Untitled")[:50]
                url = src.get("url", "")[:60]
                print(f"  [{i}] {title}")
                print(f"      {url}")
        
        print("\n" + "=" * 70)
        print("✓ Live test completed successfully!")
        print("=" * 70)
        return True
    else:
        print("\n✗ No result returned")
        return False


async def test_verifier_standalone():
    """Test the verifier agent with sample claims."""
    print("\n" + "=" * 70)
    print("Testing Verifier Agent Standalone")
    print("=" * 70)
    
    from src.core.agents import VerifierAgent, TaskAssignment, TaskType
    
    verifier = VerifierAgent()
    
    # Sample claims to verify
    claims = [
        {"text": "Water boils at 100 degrees Celsius at sea level."},
        {"text": "The Earth is the third planet from the Sun."},
        {"text": "Python was created by Guido van Rossum."},
    ]
    
    sources = [
        {
            "url": "https://en.wikipedia.org/wiki/Water",
            "title": "Water - Wikipedia",
            "content": "Water boils at 100°C (212°F) at standard atmospheric pressure."
        },
        {
            "url": "https://en.wikipedia.org/wiki/Earth",
            "title": "Earth - Wikipedia", 
            "content": "Earth is the third planet from the Sun and the only astronomical object known to harbor life."
        },
        {
            "url": "https://en.wikipedia.org/wiki/Python",
            "title": "Python Programming Language",
            "content": "Python was conceived in the late 1980s by Guido van Rossum at CWI in the Netherlands."
        }
    ]
    
    print(f"\nVerifying {len(claims)} claims against {len(sources)} sources...")
    
    task = TaskAssignment(
        task_type=TaskType.VERIFY_CLAIMS,
        agent_type="verifier",
        inputs={"claims": claims, "sources": sources}
    )
    
    result = await verifier.execute(task)
    
    print(f"\n✓ Verification complete")
    print(f"  - Status: {result.status}")
    print(f"  - Reliability Score: {result.outputs.get('reliability_score', 0):.2f}")
    
    verified = result.outputs.get("verified_claims", [])
    for claim in verified:
        status = claim.get("status", "unknown")
        conf = claim.get("confidence", 0)
        text = claim.get("claim", "")[:50]
        emoji = "✓" if status == "verified" else "?" if status == "unverified" else "✗"
        print(f"  {emoji} [{conf:.0%}] {text}...")
    
    return True


async def test_writer_standalone():
    """Test the writer agent with sample findings."""
    print("\n" + "=" * 70)
    print("Testing Writer Agent Standalone")
    print("=" * 70)
    
    from src.core.agents import WriterAgent, TaskAssignment, TaskType
    
    writer = WriterAgent()
    
    # Sample research findings
    findings = [
        {"content": "Quantum entanglement is a phenomenon where two particles become interconnected.", "url": "https://example.com/1"},
        {"content": "When particles are entangled, measuring one instantly affects the other regardless of distance.", "url": "https://example.com/2"},
        {"content": "Einstein called this 'spooky action at a distance' because it seemed to violate relativity.", "url": "https://example.com/3"},
    ]
    
    sources = [
        {"url": "https://example.com/1", "title": "Quantum Physics Basics"},
        {"url": "https://example.com/2", "title": "Understanding Entanglement"},
        {"url": "https://example.com/3", "title": "Einstein and Quantum Mechanics"},
    ]
    
    print(f"\nSynthesizing {len(findings)} findings...")
    
    result = await writer.synthesize_research(
        query="What is quantum entanglement?",
        findings=findings,
        sources=sources,
        style="brief"
    )
    
    content = result.get("content", "")
    print(f"\n✓ Synthesis complete")
    print(f"  - Word count: {result.get('word_count', 0)}")
    print(f"  - Citations: {result.get('citation_count', 0)}")
    
    print(f"\n📝 Generated Content:")
    print("-" * 50)
    print(content[:500] + ("..." if len(content) > 500 else ""))
    print("-" * 50)
    
    return True


async def main():
    """Run all live tests."""
    print("\n🚀 Starting Live Tests with gpt-oss:20b-cloud\n")
    
    # Check Ollama is running
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                print("✓ Ollama is running")
            else:
                print("✗ Ollama returned error")
                return 1
    except Exception as e:
        print(f"✗ Cannot connect to Ollama: {e}")
        print("  Make sure Ollama is running: ollama serve")
        return 1
    
    # Run tests
    tests = [
        ("Writer Standalone", test_writer_standalone),
        ("Verifier Standalone", test_verifier_standalone),
        ("Full Research Flow", test_live_research),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            result = await test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("Live Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nResult: {passed}/{len(results)} tests passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
