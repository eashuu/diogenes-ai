"""
Query Classification Service.

Classifies user queries into focus modes (like Perplexica's classifier)
to optimize search strategy and agent selection.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class FocusMode(str, Enum):
    """Available focus modes for query routing."""
    GENERAL = "general"           # Default web search + synthesis
    ACADEMIC = "academic"         # Prefer academic/scientific sources
    CODE = "code"                 # Code-focused search (GitHub, SO, docs)
    NEWS = "news"                 # Recent news/current events
    MATH = "math"                 # Math/calculation queries
    CREATIVE = "creative"         # Creative writing, brainstorming
    PERSONAL = "personal"         # Personal files / upload-based RAG


@dataclass
class ClassificationResult:
    mode: FocusMode
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "confidence": self.confidence,
            "reason": self.reason,
        }


# Pattern-based heuristic rules
_PATTERNS: list[tuple[FocusMode, list[str], float]] = [
    (FocusMode.CODE, [
        r"\b(python|javascript|typescript|rust|go|java|c\+\+|code|function|bug|error|compile|import|api|endpoint|regex|algorithm|leetcode)\b",
        r"\b(react|vue|angular|django|flask|fastapi|nextjs|node)\b",
        r"\b(git|docker|kubernetes|aws|gcp|azure)\b",
    ], 0.85),
    (FocusMode.ACADEMIC, [
        r"\b(research|study|paper|journal|thesis|hypothesis|experiment|peer.?review|meta.?analysis|citation)\b",
        r"\b(physics|chemistry|biology|neuroscience|psychology|sociology|economics)\b",
        r"\b(theorem|proof|equation|formula|arxiv|pubmed|doi)\b",
    ], 0.80),
    (FocusMode.NEWS, [
        r"\b(news|latest|today|yesterday|breaking|current events|recent|update|announcement)\b",
        r"\b(2024|2025|this week|this month)\b",
        r"\b(election|stock market|ipo|merger|scandal|crisis)\b",
    ], 0.75),
    (FocusMode.MATH, [
        r"\b(calculate|compute|solve|equation|integral|derivative|matrix|factorial|sqrt|logarithm)\b",
        r"[\d]+[\s]*[\+\-\*\/\^][\s]*[\d]+",
        r"\b(sin|cos|tan|log|ln|exp)\s*\(",
    ], 0.90),
    (FocusMode.CREATIVE, [
        r"\b(write|poem|story|essay|brainstorm|suggest|creative|fiction|dialogue|script)\b",
        r"\b(summarize|rewrite|paraphrase|translate)\b",
    ], 0.70),
]


def classify_query(
    query: str,
    file_ids: Optional[list[str]] = None,
) -> ClassificationResult:
    """
    Classify a query into a focus mode using pattern matching.

    If file_ids are provided, bias towards PERSONAL mode.
    """
    query_lower = query.lower().strip()

    # Short-circuit: if files are attached, it's a personal/upload search
    if file_ids:
        return ClassificationResult(
            mode=FocusMode.PERSONAL,
            confidence=0.95,
            reason="User uploaded files attached to query",
        )

    best_mode = FocusMode.GENERAL
    best_confidence = 0.5
    best_reason = "Default general web search."

    for mode, patterns, base_confidence in _PATTERNS:
        match_count = 0
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                match_count += 1
        if match_count > 0:
            # Boost confidence with more matches
            confidence = min(base_confidence + 0.05 * (match_count - 1), 0.99)
            if confidence > best_confidence:
                best_mode = mode
                best_confidence = confidence
                best_reason = f"Matched {match_count} {mode.value} patterns"

    return ClassificationResult(
        mode=best_mode,
        confidence=best_confidence,
        reason=best_reason,
    )


def get_search_categories(mode: FocusMode) -> list[str]:
    """Map focus mode to SearXNG search categories."""
    return {
        FocusMode.GENERAL: ["general", "science", "it"],
        FocusMode.ACADEMIC: ["science", "general"],
        FocusMode.CODE: ["it", "general"],
        FocusMode.NEWS: ["news", "general"],
        FocusMode.MATH: ["general", "science"],
        FocusMode.CREATIVE: ["general"],
        FocusMode.PERSONAL: ["general"],
    }.get(mode, ["general"])
