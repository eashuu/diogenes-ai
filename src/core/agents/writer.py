"""
Writer Agent.

Specialized agent for content synthesis and generation:
- Synthesize research findings into coherent narratives
- Generate properly cited content
- Support multiple output formats (markdown, academic, brief)
- Follow specific writing styles and templates
- Ensure claim accuracy through citation
"""

import re
from typing import Any, Optional
from dataclasses import dataclass

from src.utils.logging import get_logger
from src.core.agents.base import BaseAgent, AgentCapability
from src.core.agents.protocol import (
    TaskAssignment,
    TaskResult,
    TaskType,
)
from src.services.llm.ollama import OllamaService
from src.config import get_settings


logger = get_logger(__name__)


# Synthesis prompts for different output styles
COMPREHENSIVE_SYNTHESIS_PROMPT = """You are an expert research synthesizer. Create a comprehensive, well-structured response based on the research findings below.

QUERY: {query}

RESEARCH FINDINGS:
{findings}

VERIFIED CLAIMS (with confidence scores):
{verified_claims}

Requirements:
1. Start with a clear, direct answer to the query
2. Organize content with clear sections and headings
3. Include specific facts with inline citations [1], [2], etc.
4. Note any contradictions or areas of uncertainty
5. End with key takeaways or conclusions

Format as markdown with proper headings (##, ###).
Include a "Key Findings" section at the start.
If there are contradictions, include a "Caveats" section.
"""

BRIEF_SYNTHESIS_PROMPT = """You are an expert at providing concise, accurate answers. Create a brief but complete response to the query.

QUERY: {query}

RESEARCH FINDINGS:
{findings}

Requirements:
1. Provide a direct answer in 2-3 paragraphs
2. Include the most important facts with citations [1], [2]
3. Focus on answering the specific question asked
4. Be concise but don't omit critical information
"""

ACADEMIC_SYNTHESIS_PROMPT = """You are an academic research assistant. Create a scholarly response with rigorous citations.

QUERY: {query}

RESEARCH FINDINGS:
{findings}

VERIFIED CLAIMS:
{verified_claims}

Requirements:
1. Use formal academic language
2. Structure with Introduction, Analysis, Discussion, Conclusion
3. Include all relevant citations in academic format
4. Address limitations and areas for further research
5. Maintain objectivity and present multiple perspectives
6. Use hedging language appropriately (e.g., "suggests", "indicates")
"""

TECHNICAL_SYNTHESIS_PROMPT = """You are a technical documentation expert. Create a technical response with code examples where relevant.

QUERY: {query}

RESEARCH FINDINGS:
{findings}

Requirements:
1. Provide technical accuracy above all
2. Include code examples in proper markdown code blocks
3. Reference official documentation with citations
4. Explain technical concepts clearly
5. Include relevant warnings or best practices
6. Format for developer readability
"""


@dataclass
class SynthesisStyle:
    """Configuration for different synthesis styles."""
    name: str
    prompt_template: str
    max_length: int = 4000
    include_citations: bool = True
    include_verification: bool = True


SYNTHESIS_STYLES = {
    "comprehensive": SynthesisStyle(
        name="comprehensive",
        prompt_template=COMPREHENSIVE_SYNTHESIS_PROMPT,
        max_length=4000,
        include_citations=True,
        include_verification=True
    ),
    "brief": SynthesisStyle(
        name="brief",
        prompt_template=BRIEF_SYNTHESIS_PROMPT,
        max_length=1500,
        include_citations=True,
        include_verification=False
    ),
    "academic": SynthesisStyle(
        name="academic",
        prompt_template=ACADEMIC_SYNTHESIS_PROMPT,
        max_length=5000,
        include_citations=True,
        include_verification=True
    ),
    "technical": SynthesisStyle(
        name="technical",
        prompt_template=TECHNICAL_SYNTHESIS_PROMPT,
        max_length=4000,
        include_citations=True,
        include_verification=True
    )
}


class WriterAgent(BaseAgent):
    """
    Agent specialized in content synthesis and generation.
    
    Takes research findings, verified claims, and sources to produce
    well-structured, properly cited content.
    """
    
    def __init__(
        self,
        llm_service: Optional[OllamaService] = None,
    ):
        """
        Initialize the writer agent.
        
        Args:
            llm_service: LLM service for generation
        """
        super().__init__(
            agent_type="writer",
            capabilities=[AgentCapability.SYNTHESIS]
        )
        
        self._llm_service = llm_service
        self._settings = None
    
    @property
    def settings(self):
        """Lazy load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings
    
    @property
    def llm_service(self) -> OllamaService:
        """Lazy load LLM service."""
        if self._llm_service is None:
            self._llm_service = OllamaService(
                base_url=self.settings.llm.base_url,
                default_model=self.settings.llm.models.synthesizer,
                timeout=self.settings.llm.timeout
            )
        return self._llm_service
    
    async def execute(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a writing task.
        
        Args:
            task: The task to execute
            
        Returns:
            Generated content
        """
        task_type = task.task_type
        
        if task_type == TaskType.SYNTHESIZE_ANSWER:
            return await self._synthesize(task)
        elif task_type == TaskType.FORMAT_OUTPUT:
            return await self._format_response(task)
        elif task_type == TaskType.INSERT_CITATIONS:
            return await self._generate_citations(task)
        else:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[f"Unknown task type for writer: {task_type}"]
            )
    
    async def _synthesize(self, task: TaskAssignment) -> TaskResult:
        """
        Synthesize research findings into coherent content.
        
        Args:
            task: Task with research context
            
        Returns:
            Synthesized content
        """
        query = task.inputs.get("query", "")
        findings = task.inputs.get("findings", [])
        verified_claims = task.inputs.get("verified_claims", [])
        sources = task.inputs.get("sources", [])
        style_name = task.inputs.get("style", "comprehensive")
        
        logger.info(f"Synthesizing response for query: {query[:50]}...")
        
        # Get synthesis style
        style = SYNTHESIS_STYLES.get(style_name, SYNTHESIS_STYLES["comprehensive"])
        
        # Format findings
        findings_text = self._format_findings(findings, sources)
        
        # Format verified claims
        claims_text = self._format_verified_claims(verified_claims)
        
        # Build prompt
        prompt = style.prompt_template.format(
            query=query,
            findings=findings_text[:6000],  # Limit context
            verified_claims=claims_text[:2000] if style.include_verification else ""
        )
        
        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system="You are an expert research synthesizer. Create clear, well-cited content."
            )
            
            content = response.content
            
            # Add citations section
            if style.include_citations and sources:
                citations = self._generate_citation_section(sources)
                content = content + "\n\n" + citations
            
            # Calculate quality metrics
            metrics = self._calculate_content_metrics(content, sources)
            
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                outputs={
                    "content": content,
                    "style": style_name,
                    "word_count": len(content.split()),
                    "citation_count": len(re.findall(r'\[\d+\]', content)),
                    "metrics": metrics
                },
                confidence=metrics.get("quality_score", 0.8)
            )
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)]
            )
    
    async def _format_response(self, task: TaskAssignment) -> TaskResult:
        """
        Format content for a specific output format.
        
        Args:
            task: Task with content and format
            
        Returns:
            Formatted content
        """
        content = task.inputs.get("content", "")
        output_format = task.inputs.get("format", "markdown")
        
        if output_format == "markdown":
            # Already markdown, just clean up
            formatted = self._clean_markdown(content)
        elif output_format == "plain":
            # Strip markdown formatting
            formatted = self._strip_markdown(content)
        elif output_format == "html":
            # Convert to HTML (basic conversion)
            formatted = self._markdown_to_html(content)
        else:
            formatted = content
        
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="success",
            outputs={
                "formatted_content": formatted,
                "format": output_format
            }
        )
    
    async def _generate_citations(self, task: TaskAssignment) -> TaskResult:
        """
        Generate a citations/references section.
        
        Args:
            task: Task with sources
            
        Returns:
            Formatted citations
        """
        sources = task.inputs.get("sources", [])
        style = task.inputs.get("citation_style", "numbered")
        
        if style == "numbered":
            citations = self._generate_citation_section(sources)
        elif style == "academic":
            citations = self._generate_academic_citations(sources)
        else:
            citations = self._generate_citation_section(sources)
        
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="success",
            outputs={
                "citations": citations,
                "source_count": len(sources)
            }
        )
    
    async def _final_polish(self, task: TaskAssignment) -> TaskResult:
        """
        Final polish and quality check on content.
        
        Args:
            task: Task with content to polish
            
        Returns:
            Polished content
        """
        content = task.inputs.get("content", "")
        
        # Clean up formatting
        polished = self._clean_markdown(content)
        
        # Fix common issues
        polished = self._fix_common_issues(polished)
        
        # Calculate final quality score
        metrics = self._calculate_content_metrics(polished, [])
        
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="success",
            outputs={
                "content": polished,
                "metrics": metrics,
                "quality_score": metrics.get("quality_score", 0.8)
            },
            confidence=metrics.get("quality_score", 0.8)
        )
    
    def _format_findings(
        self,
        findings: list[dict],
        sources: list[dict]
    ) -> str:
        """Format research findings for the prompt."""
        formatted = []
        
        # Map URLs to citation numbers
        url_to_citation = {}
        for i, source in enumerate(sources, 1):
            url = source.get("url", "")
            url_to_citation[url] = i
        
        for finding in findings:
            if isinstance(finding, dict):
                content = finding.get("content", finding.get("text", str(finding)))
                url = finding.get("url", "")
                citation_num = url_to_citation.get(url, "")
                
                if citation_num:
                    formatted.append(f"[{citation_num}] {content}")
                else:
                    formatted.append(content)
            else:
                formatted.append(str(finding))
        
        return "\n\n".join(formatted)
    
    def _format_verified_claims(self, verified_claims: list[dict]) -> str:
        """Format verified claims for the prompt."""
        if not verified_claims:
            return "No claims have been verified."
        
        formatted = []
        for claim in verified_claims:
            claim_text = claim.get("claim", str(claim))
            status = claim.get("status", "unverified")
            confidence = claim.get("confidence", 0.5)
            
            status_emoji = {
                "verified": "✓",
                "disputed": "⚠",
                "refuted": "✗",
                "unverified": "?"
            }.get(status, "?")
            
            formatted.append(f"{status_emoji} [{confidence:.0%}] {claim_text}")
        
        return "\n".join(formatted)
    
    def _generate_citation_section(self, sources: list[dict]) -> str:
        """Generate a numbered citations section."""
        if not sources:
            return ""
        
        lines = ["## Sources", ""]
        
        for i, source in enumerate(sources, 1):
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            
            if url:
                lines.append(f"[{i}] [{title}]({url})")
            else:
                lines.append(f"[{i}] {title}")
        
        return "\n".join(lines)
    
    def _generate_academic_citations(self, sources: list[dict]) -> str:
        """Generate academic-style citations."""
        if not sources:
            return ""
        
        lines = ["## References", ""]
        
        for source in sources:
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            # In a real implementation, would extract author/date from content
            
            lines.append(f"- {title}. Retrieved from {url}")
        
        return "\n".join(lines)
    
    def _calculate_content_metrics(
        self,
        content: str,
        sources: list[dict]
    ) -> dict[str, Any]:
        """Calculate quality metrics for generated content."""
        word_count = len(content.split())
        citation_matches = re.findall(r'\[\d+\]', content)
        citation_count = len(citation_matches)
        unique_citations = len(set(citation_matches))
        
        # Check for structure
        has_headings = bool(re.search(r'^#{1,3}\s', content, re.MULTILINE))
        has_lists = bool(re.search(r'^[\-\*]\s', content, re.MULTILINE))
        
        # Quality scoring
        length_score = min(1.0, word_count / 500)  # Aim for ~500 words minimum
        citation_score = min(1.0, unique_citations / max(1, len(sources))) if sources else 0.8
        structure_score = 0.5 + (0.25 if has_headings else 0) + (0.25 if has_lists else 0)
        
        quality_score = (length_score * 0.3 + citation_score * 0.4 + structure_score * 0.3)
        
        return {
            "word_count": word_count,
            "citation_count": citation_count,
            "unique_citations": unique_citations,
            "has_headings": has_headings,
            "has_lists": has_lists,
            "length_score": length_score,
            "citation_score": citation_score,
            "structure_score": structure_score,
            "quality_score": quality_score
        }
    
    def _clean_markdown(self, content: str) -> str:
        """Clean up markdown formatting."""
        # Normalize line breaks
        content = content.replace('\r\n', '\n')
        
        # Fix double spaces
        content = re.sub(r'  +', ' ', content)
        
        # Fix multiple blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Ensure headings have space after #
        content = re.sub(r'^(#{1,6})([^\s#])', r'\1 \2', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def _strip_markdown(self, content: str) -> str:
        """Strip markdown formatting for plain text output."""
        # Remove headers
        content = re.sub(r'^#{1,6}\s*', '', content, flags=re.MULTILINE)
        
        # Remove bold/italic
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)
        
        # Remove links, keep text
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        
        # Remove code blocks
        content = re.sub(r'```[^`]+```', '', content)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        return content.strip()
    
    def _markdown_to_html(self, content: str) -> str:
        """Basic markdown to HTML conversion."""
        # Headers
        content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
        
        # Bold/italic
        content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', content)
        
        # Links
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', content)
        
        # Paragraphs
        paragraphs = content.split('\n\n')
        content = '\n'.join(f'<p>{p}</p>' if not p.startswith('<h') else p for p in paragraphs)
        
        return content
    
    def _fix_common_issues(self, content: str) -> str:
        """Fix common formatting issues."""
        # Fix orphaned citations
        content = re.sub(r'\s+(\[\d+\])', r' \1', content)
        
        # Fix spacing around punctuation
        content = re.sub(r'\s+([.,!?;:])', r'\1', content)
        
        # Ensure sentences end properly
        content = re.sub(r'([a-z])\n\n([A-Z])', r'\1.\n\n\2', content)
        
        return content
    
    async def synthesize_research(
        self,
        query: str,
        findings: list[dict],
        sources: list[dict],
        verified_claims: list[dict] = None,
        style: str = "comprehensive"
    ) -> dict[str, Any]:
        """
        Convenience method to synthesize research into a complete response.
        
        Args:
            query: The research query
            findings: Research findings
            sources: Sources used
            verified_claims: Verified claims (optional)
            style: Output style
            
        Returns:
            Synthesized response
        """
        task = TaskAssignment(
            task_type=TaskType.SYNTHESIZE_ANSWER,
            agent_type="writer",
            inputs={
                "query": query,
                "findings": findings,
                "sources": sources,
                "verified_claims": verified_claims or [],
                "style": style
            }
        )
        
        result = await self.execute(task)
        return result.outputs
