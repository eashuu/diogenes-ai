import asyncio
import json
import os
import sys

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.agents import ResearchOrchestrator
from src.core.agent.modes import SearchMode

async def main():
    print("==========================================")
    print("  Private AI Research Assistant (Diogenes)")
    print("==========================================")
    
    query = input("\nEnter your research topic: ")
    if not query.strip():
        print("Empty query. Exiting.")
        return

    mode_input = input("Search mode (quick/balanced/full) [balanced]: ").strip().lower() or "balanced"
    try:
        mode = SearchMode[mode_input.upper()]
    except KeyError:
        mode = SearchMode.BALANCED

    print(f"\n[1/3] Starting multi-agent research (mode={mode.value})...")
    try:
        orchestrator = ResearchOrchestrator(mode=mode)
        result = await orchestrator.research(query=query)
        
        print(f"\n[2/3] Research execution complete.")
        print(f"      - Sources found: {len(result.sources)}")
        print(f"      - Iterations: {result.iterations}")
        print(f"      - Confidence: {result.confidence:.0%}")
        print(f"      - Duration: {result.duration_seconds:.1f}s")
        
        data = {
            "query": query,
            "answer": result.answer,
            "sources": result.sources,
            "reliability_score": result.reliability_score,
            "confidence": result.confidence,
            "iterations": result.iterations,
            "duration_seconds": result.duration_seconds,
        }
        filename = "research_data.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
            
        print(f"\n[3/3] Data saved to {filename}")
        
        print("\n" + "="*42)
        print("  RESEARCH REPORT")
        print("="*42 + "\n")
        print(result.answer)
        print("\n" + "="*42)
            
    except Exception as e:
        print(f"\nERROR: Research failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
