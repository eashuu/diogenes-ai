"""
Research Agent Modes.

Defines different research modes with varying levels of depth and speed.

MODE PHILOSOPHY:
- QUICK: Speed is paramount. No verification, no iteration. Just search → synthesize.
- BALANCED: Moderate verification. Good for most queries.
- FULL: Thorough research with proper verification. Production quality.
- RESEARCH: Academic rigor. Full verification, multiple iterations, cross-referencing.
- DEEP: Exhaustive. Maximum sources, full verification, contradiction detection.
"""

from dataclasses import dataclass
from enum import Enum


class SearchMode(str, Enum):
    """
    Research mode determining depth and speed of research.
    
    Modes range from quick lookups to deep research.
    """
    QUICK = "quick"           # Fast answers, minimal crawling
    BALANCED = "balanced"     # Default mode, good balance
    FULL = "full"            # Thorough research, more sources
    RESEARCH = "research"     # Academic-level research
    DEEP = "deep"            # Exhaustive deep research


@dataclass
class ModeConfig:
    """
    Configuration for a specific research mode.
    
    Attributes:
        max_search_results: Maximum results per search query
        max_sources_to_crawl: Maximum URLs to crawl
        max_chunks_for_synthesis: Maximum chunks to send to LLM
        max_sources_for_synthesis: Maximum sources to use
        max_iterations: Maximum reflection iterations
        enable_reflection: Whether to enable reflection/review phase
        enable_verification: Whether to enable claim verification
        enable_contradiction_check: Whether to check for contradictions
        enable_planning: Whether to do LLM-based query planning
        min_quality_score: Minimum quality score for sources
        crawl_timeout: Timeout for crawling in seconds
        synthesis_style: Style for synthesis (concise, balanced, comprehensive, academic)
        target_word_count: Target word count for answer (0 = no limit)
    """
    max_search_results: int
    max_sources_to_crawl: int
    max_chunks_for_synthesis: int
    max_sources_for_synthesis: int
    max_iterations: int
    enable_reflection: bool
    enable_verification: bool
    enable_contradiction_check: bool
    enable_planning: bool
    min_quality_score: float
    crawl_timeout: float
    synthesis_style: str
    target_word_count: int


# Mode configurations optimized for their use cases
MODE_CONFIGS: dict[SearchMode, ModeConfig] = {
    # QUICK: Speed-focused. No verification, no planning, just fast answers.
    # Use case: Quick factual lookups, simple questions, time-sensitive queries
    SearchMode.QUICK: ModeConfig(
        max_search_results=3,           # Fewer searches (was 5)
        max_sources_to_crawl=2,         # Minimal crawling (was 3)
        max_chunks_for_synthesis=15,    # Less context (was 20)
        max_sources_for_synthesis=2,    # Just 2 sources (was 3)
        max_iterations=0,               # NO iterations (was 1)
        enable_reflection=False,        # No reflection
        enable_verification=False,      # NO verification - key for speed
        enable_contradiction_check=False,  # No contradiction check
        enable_planning=False,          # NO LLM planning - just use query directly
        min_quality_score=0.6,          # Higher threshold = faster (less to process)
        crawl_timeout=15.0,             # Fast timeout (was 30)
        synthesis_style="concise",      # Short answers
        target_word_count=150,          # ~1 paragraph
    ),
    
    # BALANCED: Good mix of speed and quality. Light verification.
    # Use case: General questions, everyday research, most common queries
    SearchMode.BALANCED: ModeConfig(
        max_search_results=8,           # Moderate searches (was 10)
        max_sources_to_crawl=10,        # Moderate crawling (was 15)
        max_chunks_for_synthesis=40,    # Reasonable context (was 50)
        max_sources_for_synthesis=5,    # 5 sources for citations
        max_iterations=1,               # 1 optional iteration (was 3)
        enable_reflection=True,         # Check if more needed
        enable_verification=True,       # Light verification
        enable_contradiction_check=False,  # Skip contradiction check (slower)
        enable_planning=True,           # Do query planning
        min_quality_score=0.5,          # Moderate threshold
        crawl_timeout=45.0,             # Reasonable timeout (was 60)
        synthesis_style="balanced",     # Balanced detail
        target_word_count=300,          # ~2-3 paragraphs
    ),
    
    # FULL: Thorough research. Full verification, multiple iterations.
    # Use case: Important decisions, thorough understanding needed
    SearchMode.FULL: ModeConfig(
        max_search_results=12,          # More searches (was 15)
        max_sources_to_crawl=20,        # Good coverage (was 25)
        max_chunks_for_synthesis=80,    # Rich context (was 100)
        max_sources_for_synthesis=8,    # Multiple sources
        max_iterations=2,               # Up to 2 iterations (was 5)
        enable_reflection=True,         # Review and iterate
        enable_verification=True,       # Full verification
        enable_contradiction_check=True,   # Check contradictions
        enable_planning=True,           # Full planning
        min_quality_score=0.4,          # Accept more sources
        crawl_timeout=60.0,             # Patient crawling (was 90)
        synthesis_style="comprehensive",  # Detailed answers
        target_word_count=500,          # ~4-5 paragraphs
    ),
    
    # RESEARCH: Academic rigor. Exhaustive verification, cross-referencing.
    # Use case: Academic research, fact-checking, investigative queries
    SearchMode.RESEARCH: ModeConfig(
        max_search_results=15,          # Many searches (was 20)
        max_sources_to_crawl=30,        # Extensive crawling (was 40)
        max_chunks_for_synthesis=120,   # Deep context (was 150)
        max_sources_for_synthesis=12,   # Many sources for citations
        max_iterations=3,               # Multiple iterations (was 7)
        enable_reflection=True,         # Critical review
        enable_verification=True,       # Rigorous verification
        enable_contradiction_check=True,   # Detect conflicts
        enable_planning=True,           # Strategic planning
        min_quality_score=0.3,          # Include more diverse sources
        crawl_timeout=90.0,             # Patient (was 120)
        synthesis_style="academic",     # Formal, cited
        target_word_count=800,          # Detailed response
    ),
    
    # DEEP: Maximum thoroughness. Leave no stone unturned.
    # Use case: Critical research, maximum accuracy needed, thesis-level
    SearchMode.DEEP: ModeConfig(
        max_search_results=20,          # Maximum searches (was 30)
        max_sources_to_crawl=40,        # Maximum crawling (was 60)
        max_chunks_for_synthesis=150,   # Maximum context (was 200)
        max_sources_for_synthesis=15,   # Maximum citations
        max_iterations=5,               # Many iterations (was 10)
        enable_reflection=True,         # Deep review
        enable_verification=True,       # Maximum verification
        enable_contradiction_check=True,   # Full conflict detection
        enable_planning=True,           # Comprehensive planning
        min_quality_score=0.2,          # Cast wide net
        crawl_timeout=120.0,            # Very patient (was 180)
        synthesis_style="academic",     # Formal, exhaustive
        target_word_count=1200,         # Long-form response
    ),
}


def get_mode_config(mode: SearchMode) -> ModeConfig:
    """
    Get configuration for a specific mode.
    
    Args:
        mode: The search mode
        
    Returns:
        Mode configuration
        
    Raises:
        ValueError: If mode is not recognized
    """
    if mode not in MODE_CONFIGS:
        raise ValueError(f"Unknown search mode: {mode}")
    return MODE_CONFIGS[mode]


def get_mode_description(mode: SearchMode) -> str:
    """
    Get human-readable description of a mode.
    
    Args:
        mode: The search mode
        
    Returns:
        Description string
    """
    descriptions = {
        SearchMode.QUICK: "Fastest answers, no verification (~10-15s, 2 sources)",
        SearchMode.BALANCED: "Good balance with light verification (~1-2min, 5 sources)",
        SearchMode.FULL: "Thorough research with full verification (~3-5min, 8 sources)",
        SearchMode.RESEARCH: "Academic rigor with cross-referencing (~5-10min, 12 sources)",
        SearchMode.DEEP: "Exhaustive research with maximum accuracy (~10-20min, 15+ sources)",
    }
    return descriptions.get(mode, "Unknown mode")
