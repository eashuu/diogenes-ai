"""
Research Profiles.

Specialized configurations for different research domains.
Each profile customizes search strategies, verification rules,
and output formatting for specific use cases.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from src.core.agent.modes import SearchMode


class ProfileType(str, Enum):
    """Available research profile types."""
    GENERAL = "general"
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    NEWS = "news"
    MEDICAL = "medical"
    LEGAL = "legal"
    CREATIVE = "creative"
    BUSINESS = "business"


@dataclass
class SearchStrategy:
    """Configuration for search behavior."""
    # Search engines to prioritize
    engines: list[str] = field(default_factory=lambda: ["google", "bing", "duckduckgo"])
    # Search categories to use
    categories: list[str] = field(default_factory=lambda: ["general"])
    # Time filter (None, "day", "week", "month", "year")
    time_filter: Optional[str] = None
    # Preferred domains to prioritize
    preferred_domains: list[str] = field(default_factory=list)
    # Domains to avoid
    blocked_domains: list[str] = field(default_factory=list)
    # Additional search operators/modifiers
    search_operators: list[str] = field(default_factory=list)


@dataclass
class VerificationConfig:
    """Configuration for verification behavior."""
    # Minimum confidence threshold
    min_confidence: float = 0.6
    # Required number of corroborating sources
    min_corroboration: int = 2
    # Weight for domain authority scoring
    domain_authority_weight: float = 0.3
    # Weight for content freshness
    freshness_weight: float = 0.2
    # Require primary sources
    require_primary_sources: bool = False
    # Strict fact-checking mode
    strict_mode: bool = False


@dataclass
class OutputConfig:
    """Configuration for output formatting."""
    # Default synthesis style
    default_style: str = "comprehensive"
    # Include confidence scores
    show_confidence: bool = True
    # Include source reliability ratings
    show_reliability: bool = True
    # Citation style (numbered, academic, inline)
    citation_style: str = "numbered"
    # Maximum response length (words)
    max_length: int = 2000
    # Include methodology section
    include_methodology: bool = False


@dataclass
class ResearchProfile:
    """Complete research profile configuration."""
    profile_type: ProfileType
    name: str
    description: str
    default_mode: SearchMode
    search_strategy: SearchStrategy
    verification: VerificationConfig
    output: OutputConfig
    # System prompt additions for this profile
    system_prompt_additions: str = ""
    # Query preprocessing rules
    query_enhancements: list[str] = field(default_factory=list)


# Predefined profiles
GENERAL_PROFILE = ResearchProfile(
    profile_type=ProfileType.GENERAL,
    name="General Research",
    description="Balanced profile for general questions and topics",
    default_mode=SearchMode.BALANCED,
    search_strategy=SearchStrategy(
        engines=["google", "bing", "duckduckgo"],
        categories=["general"],
    ),
    verification=VerificationConfig(
        min_confidence=0.6,
        min_corroboration=2,
    ),
    output=OutputConfig(
        default_style="comprehensive",
        max_length=2000,
    ),
)

ACADEMIC_PROFILE = ResearchProfile(
    profile_type=ProfileType.ACADEMIC,
    name="Academic Research",
    description="Rigorous research with peer-reviewed sources",
    default_mode=SearchMode.RESEARCH,
    search_strategy=SearchStrategy(
        engines=["google scholar", "semantic scholar", "pubmed"],
        categories=["science", "general"],
        preferred_domains=[
            ".edu", ".gov", "arxiv.org", "nature.com", "science.org",
            "springer.com", "wiley.com", "elsevier.com", "pubmed.ncbi",
            "scholar.google.com", "researchgate.net"
        ],
        search_operators=["site:scholar.google.com OR site:arxiv.org OR site:.edu"],
    ),
    verification=VerificationConfig(
        min_confidence=0.8,
        min_corroboration=3,
        require_primary_sources=True,
        strict_mode=True,
        domain_authority_weight=0.5,
    ),
    output=OutputConfig(
        default_style="academic",
        citation_style="academic",
        max_length=3000,
        include_methodology=True,
        show_confidence=True,
        show_reliability=True,
    ),
    system_prompt_additions="""
You are conducting academic research. Prioritize:
- Peer-reviewed sources and primary research
- Precise citations with author, year, and DOI when available
- Acknowledgment of limitations and alternative viewpoints
- Formal academic language and hedging where appropriate
""",
    query_enhancements=["research", "study", "peer-reviewed"],
)

TECHNICAL_PROFILE = ResearchProfile(
    profile_type=ProfileType.TECHNICAL,
    name="Technical Documentation",
    description="Programming and technical documentation research",
    default_mode=SearchMode.BALANCED,
    search_strategy=SearchStrategy(
        engines=["google", "bing"],
        categories=["it", "general"],
        preferred_domains=[
            "docs.python.org", "developer.mozilla.org", "docs.microsoft.com",
            "github.com", "stackoverflow.com", "docs.aws.amazon.com",
            "cloud.google.com/docs", "kubernetes.io/docs",
            "reactjs.org", "vuejs.org", "angular.io",
        ],
        search_operators=["site:stackoverflow.com OR site:github.com OR site:docs"],
    ),
    verification=VerificationConfig(
        min_confidence=0.7,
        min_corroboration=2,
        freshness_weight=0.4,  # Technical docs should be recent
    ),
    output=OutputConfig(
        default_style="technical",
        citation_style="numbered",
        max_length=2500,
        show_confidence=False,  # Technical answers should be definitive
    ),
    system_prompt_additions="""
You are a technical documentation assistant. Prioritize:
- Official documentation over blog posts
- Working code examples with proper formatting
- Version-specific information when relevant
- Best practices and common pitfalls
""",
    query_enhancements=["documentation", "example", "tutorial"],
)

NEWS_PROFILE = ResearchProfile(
    profile_type=ProfileType.NEWS,
    name="News & Current Events",
    description="Recent news and current events research",
    default_mode=SearchMode.QUICK,
    search_strategy=SearchStrategy(
        engines=["google news", "bing news"],
        categories=["news", "general"],
        time_filter="week",  # Focus on recent news
        preferred_domains=[
            "reuters.com", "apnews.com", "bbc.com", "npr.org",
            "nytimes.com", "washingtonpost.com", "theguardian.com",
            "economist.com", "wsj.com", "ft.com",
        ],
        blocked_domains=[
            # Avoid known low-quality or hyper-partisan sources
        ],
    ),
    verification=VerificationConfig(
        min_confidence=0.7,
        min_corroboration=2,
        freshness_weight=0.5,  # Recency is critical for news
    ),
    output=OutputConfig(
        default_style="brief",
        max_length=1500,
        show_reliability=True,
    ),
    system_prompt_additions="""
You are a news research assistant. Prioritize:
- Verified facts from reputable news sources
- Multiple perspectives on events
- Clear distinction between facts and opinions
- Dates and timeline of events
""",
)

MEDICAL_PROFILE = ResearchProfile(
    profile_type=ProfileType.MEDICAL,
    name="Medical Research",
    description="Medical and health information research (NOT for diagnosis)",
    default_mode=SearchMode.RESEARCH,
    search_strategy=SearchStrategy(
        engines=["pubmed", "google scholar"],
        categories=["science", "general"],
        preferred_domains=[
            "ncbi.nlm.nih.gov", "nih.gov", "who.int", "cdc.gov",
            "mayoclinic.org", "webmd.com", "uptodate.com",
            "cochrane.org", "nejm.org", "thelancet.com",
        ],
        blocked_domains=[
            # Avoid unverified health advice sites
        ],
    ),
    verification=VerificationConfig(
        min_confidence=0.85,
        min_corroboration=3,
        require_primary_sources=True,
        strict_mode=True,
    ),
    output=OutputConfig(
        default_style="comprehensive",
        max_length=2500,
        show_confidence=True,
        show_reliability=True,
        include_methodology=True,
    ),
    system_prompt_additions="""
IMPORTANT: You are providing general medical information for educational purposes only.
Always include a disclaimer that this is not medical advice.
Prioritize:
- Peer-reviewed clinical research
- Official health organization guidelines
- Clear evidence levels for claims
- Known limitations and side effects
""",
    query_enhancements=["clinical", "research", "evidence"],
)

LEGAL_PROFILE = ResearchProfile(
    profile_type=ProfileType.LEGAL,
    name="Legal Research",
    description="Legal information research (NOT legal advice)",
    default_mode=SearchMode.RESEARCH,
    search_strategy=SearchStrategy(
        engines=["google", "bing"],
        categories=["general"],
        preferred_domains=[
            ".gov", "law.cornell.edu", "justia.com", "oyez.org",
            "supremecourt.gov", "uscourts.gov", "law.com",
        ],
    ),
    verification=VerificationConfig(
        min_confidence=0.8,
        min_corroboration=2,
        require_primary_sources=True,
    ),
    output=OutputConfig(
        default_style="comprehensive",
        citation_style="academic",
        max_length=2500,
        show_reliability=True,
    ),
    system_prompt_additions="""
IMPORTANT: You are providing general legal information for educational purposes only.
Always include a disclaimer that this is not legal advice.
Prioritize:
- Primary legal sources (statutes, case law, regulations)
- Jurisdiction-specific information
- Clear citations to legal authorities
""",
)

CREATIVE_PROFILE = ResearchProfile(
    profile_type=ProfileType.CREATIVE,
    name="Creative Research",
    description="Research for creative writing and worldbuilding",
    default_mode=SearchMode.FULL,
    search_strategy=SearchStrategy(
        engines=["google", "bing", "duckduckgo"],
        categories=["general", "images"],
        preferred_domains=[
            "wikipedia.org", "britannica.com", "worldbuilding.stackexchange.com",
        ],
    ),
    verification=VerificationConfig(
        min_confidence=0.5,  # Lower threshold for creative research
        min_corroboration=1,
        strict_mode=False,
    ),
    output=OutputConfig(
        default_style="comprehensive",
        max_length=3000,
        show_confidence=False,
        show_reliability=False,
    ),
    system_prompt_additions="""
You are assisting with creative research. Prioritize:
- Rich, detailed information for worldbuilding
- Historical and cultural context
- Diverse perspectives and ideas
- Both factual information and creative inspiration
""",
)

BUSINESS_PROFILE = ResearchProfile(
    profile_type=ProfileType.BUSINESS,
    name="Business Research",
    description="Market research and business intelligence",
    default_mode=SearchMode.BALANCED,
    search_strategy=SearchStrategy(
        engines=["google", "bing"],
        categories=["general", "news"],
        preferred_domains=[
            "bloomberg.com", "reuters.com", "wsj.com", "ft.com",
            "hbr.org", "mckinsey.com", "statista.com",
            "sec.gov", "crunchbase.com",
        ],
        time_filter="year",  # Business data should be recent
    ),
    verification=VerificationConfig(
        min_confidence=0.7,
        min_corroboration=2,
        freshness_weight=0.4,
    ),
    output=OutputConfig(
        default_style="comprehensive",
        max_length=2000,
        show_confidence=True,
    ),
    system_prompt_additions="""
You are a business research assistant. Prioritize:
- Verified financial data and market statistics
- Industry trends and competitive analysis
- Clear sourcing for all claims
- Both qualitative and quantitative insights
""",
)


# Profile registry
PROFILES: dict[ProfileType, ResearchProfile] = {
    ProfileType.GENERAL: GENERAL_PROFILE,
    ProfileType.ACADEMIC: ACADEMIC_PROFILE,
    ProfileType.TECHNICAL: TECHNICAL_PROFILE,
    ProfileType.NEWS: NEWS_PROFILE,
    ProfileType.MEDICAL: MEDICAL_PROFILE,
    ProfileType.LEGAL: LEGAL_PROFILE,
    ProfileType.CREATIVE: CREATIVE_PROFILE,
    ProfileType.BUSINESS: BUSINESS_PROFILE,
}


def get_profile(profile_type: ProfileType) -> ResearchProfile:
    """Get a research profile by type."""
    return PROFILES.get(profile_type, GENERAL_PROFILE)


def detect_profile(query: str) -> ProfileType:
    """
    Attempt to detect the best profile for a query.
    
    Args:
        query: The research query
        
    Returns:
        Detected profile type
    """
    query_lower = query.lower()
    
    # Technical indicators
    if any(kw in query_lower for kw in [
        "code", "programming", "api", "function", "class", "python",
        "javascript", "typescript", "rust", "error", "bug", "debug",
        "docker", "kubernetes", "aws", "azure", "github"
    ]):
        return ProfileType.TECHNICAL
    
    # Academic indicators
    if any(kw in query_lower for kw in [
        "research", "study", "paper", "journal", "peer-reviewed",
        "hypothesis", "methodology", "citation", "academic"
    ]):
        return ProfileType.ACADEMIC
    
    # Medical indicators
    if any(kw in query_lower for kw in [
        "symptoms", "treatment", "diagnosis", "disease", "medication",
        "doctor", "medical", "health", "clinical", "patient"
    ]):
        return ProfileType.MEDICAL
    
    # Legal indicators
    if any(kw in query_lower for kw in [
        "law", "legal", "court", "statute", "regulation", "attorney",
        "lawsuit", "contract", "rights", "constitutional"
    ]):
        return ProfileType.LEGAL
    
    # News indicators
    if any(kw in query_lower for kw in [
        "news", "today", "yesterday", "recent", "latest", "breaking",
        "announced", "election", "politics"
    ]):
        return ProfileType.NEWS
    
    # Business indicators
    if any(kw in query_lower for kw in [
        "market", "company", "stock", "revenue", "profit", "startup",
        "investment", "business", "industry", "competitor"
    ]):
        return ProfileType.BUSINESS
    
    # Creative indicators
    if any(kw in query_lower for kw in [
        "story", "writing", "fiction", "fantasy", "worldbuilding",
        "character", "plot", "narrative", "creative"
    ]):
        return ProfileType.CREATIVE
    
    return ProfileType.GENERAL
