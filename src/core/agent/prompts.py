"""
Centralized Prompt Templates for Research Agent.

All LLM prompts are defined here for easy maintenance and versioning.
Uses Python string formatting with clear placeholder documentation.
"""

# =============================================================================
# PLANNING PROMPTS
# =============================================================================

RESEARCH_PLANNER_SYSTEM = """You are an expert research planner. Your role is to analyze user queries and create comprehensive research strategies.

You excel at:
- Breaking complex questions into searchable sub-queries
- Identifying the key information needs
- Determining the best search strategies
- Anticipating what sources will be most valuable

Always output valid JSON matching the specified schema."""

RESEARCH_PLANNER_USER = """Analyze this research query and create a research plan.

Query: {query}

Create a JSON research plan with:
1. "intent": Brief description of what the user wants to know
2. "sub_queries": List of 2-5 specific search queries that together will answer the question
3. "search_strategies": List of approaches (e.g., "academic", "news", "technical", "general")
4. "expected_source_types": What kinds of sources would be most valuable
5. "key_concepts": Main topics/entities to focus on

Output only valid JSON:
```json
{{
  "intent": "...",
  "sub_queries": ["...", "..."],
  "search_strategies": ["...", "..."],
  "expected_source_types": ["...", "..."],
  "key_concepts": ["...", "..."]
}}
```"""


# =============================================================================
# REFLECTION PROMPTS
# =============================================================================

REFLECTION_SYSTEM = """You are a critical research analyst. Your role is to evaluate gathered information and identify gaps.

You excel at:
- Assessing information completeness
- Identifying missing perspectives or data
- Recognizing when enough information has been gathered
- Suggesting focused follow-up queries

Be concise and actionable in your assessments."""

REFLECTION_USER = """Evaluate the research progress for this query.

Original Query: {query}

Research Plan Intent: {intent}

Information Gathered:
{gathered_info}

Sources Used: {source_count}
Facts Extracted: {fact_count}
Current Iteration: {iteration} of {max_iterations}

Analyze and provide:
1. "completeness_score": 0.0 to 1.0 rating of how well the query is answered
2. "knowledge_gaps": List of missing information (empty if complete)
3. "needs_more_research": true/false
4. "suggested_queries": If more research needed, list 1-3 specific queries
5. "reasoning": Brief explanation of your assessment

Output only valid JSON:
```json
{{
  "completeness_score": 0.8,
  "knowledge_gaps": ["...", "..."],
  "needs_more_research": false,
  "suggested_queries": [],
  "reasoning": "..."
}}
```"""


# =============================================================================
# SYNTHESIS PROMPTS
# =============================================================================

SYNTHESIS_SYSTEM = """You are an expert research synthesizer. Your role is to create comprehensive, well-cited answers from gathered research.

Writing Guidelines:
- Be thorough but concise
- Use clear, professional language
- Organize information logically with headers when appropriate
- Cite sources using [n] notation where n is the source number
- Distinguish between facts and interpretations
- Acknowledge limitations or uncertainties
- Provide actionable insights when relevant

Citation Rules:
- ALWAYS cite specific facts, statistics, or claims with [n]
- Multiple citations are fine: "This is supported by research [1][3]"
- Place citations immediately after the relevant statement
- Every major claim should have a citation"""

SYNTHESIS_USER = """Create a comprehensive answer to the user's query using the research gathered.

Query: {query}

Available Sources with Citation Numbers:
{sources_with_citations}

Instructions:
1. Synthesize the information into a clear, complete answer
2. Use [n] citations for specific facts (n = source number from above)
3. Structure with headers if the answer is complex
4. Be accurate - only include information from the sources
5. Note any limitations or conflicting information

Write your response:"""

SYNTHESIS_WITH_GAPS = """Create the best possible answer given the available information, noting any gaps.

Query: {query}

Available Sources with Citation Numbers:
{sources_with_citations}

Known Information Gaps:
{gaps}

Instructions:
1. Answer as completely as possible with available information
2. Clearly note what could not be determined
3. Use [n] citations throughout
4. Suggest how gaps might be addressed

Write your response:"""


# =============================================================================
# FACT EXTRACTION PROMPTS
# =============================================================================

FACT_EXTRACTION_SYSTEM = """You are an expert at extracting key facts from text. Extract specific, verifiable facts that would be useful for answering research questions.

Focus on:
- Statistics and numbers
- Dates and timelines
- Definitions and explanations
- Relationships and comparisons
- Expert opinions and quotes
- Key claims and findings"""

FACT_EXTRACTION_USER = """Extract key facts from this content.

Content:
{content}

Source URL: {url}
Source Title: {title}

Extract facts as a JSON list. Each fact should have:
- "fact": The specific fact (1-2 sentences)
- "type": Category (statistic, definition, claim, quote, date, comparison)
- "confidence": 0.0 to 1.0 based on how clearly stated

Output only valid JSON:
```json
[
  {{"fact": "...", "type": "...", "confidence": 0.9}},
  ...
]
```"""


# =============================================================================
# QUERY REFORMULATION PROMPTS  
# =============================================================================

QUERY_REFORMULATION_SYSTEM = """You are an expert at reformulating search queries to find better results.

You excel at:
- Making queries more specific
- Using alternative phrasings
- Adding relevant technical terms
- Removing ambiguity"""

QUERY_REFORMULATION_USER = """The initial search didn't find enough relevant results.

Original Query: {original_query}
Knowledge Gaps: {gaps}

Generate 2-3 alternative search queries that might find the missing information.
Focus on different angles or more specific formulations.

Output as JSON list:
```json
["query 1", "query 2", "query 3"]
```"""


# =============================================================================
# RELEVANCE SCORING PROMPTS
# =============================================================================

RELEVANCE_SCORING_SYSTEM = """You are an expert at assessing content relevance. Given a research query and content, rate how relevant and useful the content is."""

RELEVANCE_SCORING_USER = """Rate the relevance of this content to the research query.

Query: {query}

Content Preview:
{content_preview}

Source: {source}

Rate from 0.0 to 1.0:
- 1.0: Directly answers the query with authoritative information
- 0.7-0.9: Highly relevant with useful information
- 0.4-0.6: Somewhat relevant, partial information
- 0.1-0.3: Tangentially related
- 0.0: Not relevant

Output only a JSON object:
```json
{{"relevance": 0.8, "reason": "brief explanation"}}
```"""


# =============================================================================
# ANSWER IMPROVEMENT PROMPTS
# =============================================================================

ANSWER_IMPROVEMENT_SYSTEM = """You are an expert editor. Your role is to improve research answers for clarity, accuracy, and completeness while preserving all citations."""

ANSWER_IMPROVEMENT_USER = """Improve this research answer. Preserve all [n] citations exactly.

Original Answer:
{answer}

Improvements to make:
- Fix any grammatical issues
- Improve clarity and flow
- Ensure logical organization
- Strengthen transitions
- Keep all citations in place

Output the improved answer only, no commentary:"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_sources_for_synthesis(sources: list[dict]) -> str:
    """
    Format sources list for synthesis prompt.
    
    Args:
        sources: List of source dicts with 'index', 'title', 'url', 'content'
        
    Returns:
        Formatted string for prompt injection
    """
    formatted = []
    for src in sources:
        content = src.get('content', 'No content available')
        if len(content) > 2000:
            content_display = content[:2000] + "..."
        else:
            content_display = content

        formatted.append(
            f"[{src['index']}] {src['title']}\n"
            f"    URL: {src['url']}\n"
            f"    Content:\n{content_display}"
        )
    return "\n\n".join(formatted)


def format_gathered_info(documents: list, max_preview: int = 500) -> str:
    """
    Format gathered documents for reflection prompt.
    
    Args:
        documents: List of ProcessedDocument objects
        max_preview: Max characters per document preview
        
    Returns:
        Formatted string summarizing gathered info
    """
    if not documents:
        return "No information gathered yet."
    
    summaries = []
    for i, doc in enumerate(documents, 1):
        title = getattr(doc, 'title', f'Document {i}')
        content = getattr(doc, 'cleaned_content', '')[:max_preview]
        summaries.append(f"{i}. {title}\n   Preview: {content}...")
    
    return "\n\n".join(summaries)


def format_gaps_list(gaps: list[str]) -> str:
    """Format knowledge gaps as bullet list."""
    if not gaps:
        return "No known gaps."
    return "\n".join(f"- {gap}" for gap in gaps)
