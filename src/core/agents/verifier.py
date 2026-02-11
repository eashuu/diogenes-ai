"""
Verifier Agent.

Specialized agent for fact-checking and source verification:
- Cross-reference facts across multiple sources
- Detect contradictions and inconsistencies
- Assess source reliability
- Identify potential biases
- Flag uncertain or controversial claims
"""

import asyncio
from typing import Any, Optional
from dataclasses import dataclass

from src.utils.logging import get_logger
from src.core.agents.base import BaseAgent, AgentCapability
from src.core.agents.protocol import (
    TaskAssignment,
    TaskResult,
    TaskType,
    VerifiedClaim,
    Contradiction,
)
from src.services.llm.ollama import OllamaService
from src.config import get_settings


logger = get_logger(__name__)


# Prompts for verification
CLAIM_VERIFICATION_PROMPT = """You are a fact-checking expert. Analyze whether the following claim is supported by the provided sources.

CLAIM: {claim}

SOURCES:
{sources}

Determine:
1. Is this claim supported, contradicted, or unverified by the sources?
2. What is your confidence level (0.0 to 1.0)?
3. Which sources support it? Which contradict it?

Respond in JSON format:
{{
    "status": "verified|disputed|refuted|unverified",
    "confidence": 0.0-1.0,
    "supporting_sources": ["url1", "url2"],
    "contradicting_sources": ["url3"],
    "explanation": "Brief explanation"
}}
"""

CONTRADICTION_DETECTION_PROMPT = """You are a logical analysis expert. Check if these two claims contradict each other.

CLAIM 1: {claim1}
CLAIM 2: {claim2}

Determine:
1. Do these claims contradict each other?
2. If yes, how severe is the contradiction (minor, moderate, major)?
3. Explain the contradiction if one exists.

Respond in JSON format:
{{
    "is_contradiction": true|false,
    "severity": "none|minor|moderate|major",
    "explanation": "Brief explanation"
}}
"""

BATCH_CONTRADICTION_PROMPT = """You are a logical analysis expert. Analyze the following numbered claims for ANY contradictions between them.

CLAIMS:
{claims}

Instructions:
- Compare all claims against each other.
- Identify every pair of claims that contradict each other.
- Only report actual contradictions, not mere differences in detail.
- If no contradictions exist, return an empty list.

Respond in JSON format:
{{
    "contradictions": [
        {{
            "claim1_index": 0,
            "claim2_index": 1,
            "severity": "minor|moderate|major",
            "explanation": "Brief explanation"
        }}
    ]
}}
"""

BIAS_DETECTION_PROMPT = """You are a media literacy expert. Analyze the following content for potential bias.

CONTENT: {content}
SOURCE: {source}

Identify:
1. Political or ideological bias
2. Commercial bias (promoting products/services)
3. Sensationalism or emotional manipulation
4. Cherry-picking of facts
5. Missing context or perspective

Respond in JSON format:
{{
    "bias_detected": true|false,
    "bias_types": ["type1", "type2"],
    "bias_score": 0.0-1.0,
    "explanation": "Brief explanation",
    "missing_perspectives": ["perspective1", "perspective2"]
}}
"""


class VerifierAgent(BaseAgent):
    """
    Agent specialized in fact-checking and source verification.
    
    This is what sets Diogenes apart - rigorous verification of claims
    with explicit confidence scores and source attribution.
    """
    
    def __init__(
        self,
        llm_service: Optional[OllamaService] = None,
    ):
        """
        Initialize the verifier agent.
        
        Args:
            llm_service: LLM service for analysis
        """
        super().__init__(
            agent_type="verifier",
            capabilities=[AgentCapability.VERIFICATION]
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
        Execute a verification task.
        
        Args:
            task: The task to execute
            
        Returns:
            Verification results
        """
        task_type = task.task_type
        
        if task_type == TaskType.VERIFY_CLAIMS:
            return await self._verify_claims(task)
        elif task_type == TaskType.CHECK_CONTRADICTIONS:
            return await self._check_contradictions(task)
        elif task_type == TaskType.ASSESS_RELIABILITY:
            return await self._assess_reliability(task)
        else:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[f"Unknown task type for verifier: {task_type}"]
            )
    
    async def _verify_claims(self, task: TaskAssignment) -> TaskResult:
        """
        Verify claims against available sources.
        
        Args:
            task: Task with claims and sources
            
        Returns:
            Verified claims with confidence scores
        """
        claims = task.inputs.get("claims", [])
        sources = task.inputs.get("sources", [])
        
        if not claims:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                outputs={"verified_claims": [], "reliability_score": 1.0}
            )
        
        logger.info(f"Verifying {len(claims)} claims against {len(sources)} sources")
        
        # Format sources for the prompt
        source_text = self._format_sources(sources)
        
        verified_claims = []
        
        # Verify each claim
        for claim in claims:
            if isinstance(claim, dict):
                claim_text = claim.get("text", claim.get("fact", str(claim)))
            else:
                claim_text = str(claim)
            
            try:
                verification = await self._verify_single_claim(claim_text, source_text)
                verified_claims.append(verification)
            except Exception as e:
                logger.warning(f"Failed to verify claim: {e}")
                verified_claims.append({
                    "claim": claim_text,
                    "status": "unverified",
                    "confidence": 0.5,
                    "error": str(e)
                })
        
        # Calculate overall reliability
        reliability_score = self._calculate_reliability(verified_claims)
        
        # Find contradictions
        contradictions = await self._find_contradictions_in_claims(verified_claims)
        
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="success",
            outputs={
                "verified_claims": verified_claims,
                "contradictions": contradictions,
                "reliability_score": reliability_score,
                "verified_count": len([c for c in verified_claims if c.get("status") == "verified"]),
                "disputed_count": len([c for c in verified_claims if c.get("status") == "disputed"]),
                "unverified_count": len([c for c in verified_claims if c.get("status") == "unverified"])
            },
            confidence=reliability_score
        )
    
    async def _verify_single_claim(
        self,
        claim: str,
        source_text: str
    ) -> dict[str, Any]:
        """Verify a single claim against sources."""
        import json
        
        prompt = CLAIM_VERIFICATION_PROMPT.format(
            claim=claim,
            sources=source_text[:4000]  # Limit context
        )
        
        response = await self.llm_service.generate(
            prompt=prompt,
            system="You are a fact-checking assistant. Always respond with valid JSON."
        )
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            result["claim"] = claim
            return result
            
        except json.JSONDecodeError:
            return {
                "claim": claim,
                "status": "unverified",
                "confidence": 0.5,
                "explanation": "Could not parse verification result"
            }
    
    async def _check_contradictions(self, task: TaskAssignment) -> TaskResult:
        """
        Check for contradictions between claims.
        
        Args:
            task: Task with claims to check
            
        Returns:
            List of detected contradictions
        """
        claims = task.inputs.get("claims", [])
        
        if len(claims) < 2:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                outputs={"contradictions": []}
            )
        
        contradictions = await self._find_contradictions_in_claims(claims)
        
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="success",
            outputs={
                "contradictions": contradictions,
                "contradiction_count": len(contradictions)
            },
            confidence=1.0 if not contradictions else 0.7
        )
    
    async def _find_contradictions_in_claims(
        self,
        claims: list[dict]
    ) -> list[dict]:
        """Find contradictions between claims using a single batched LLM call.

        Previous implementation made up to 10 pairwise LLM calls (O(N²)).
        This version sends all claims in one prompt, reducing to O(1) LLM calls.
        """
        import json
        
        # Extract claim texts
        claim_texts = [
            c.get("claim", str(c)) if isinstance(c, dict) else str(c)
            for c in claims
        ]
        
        if len(claim_texts) < 2:
            return []

        # Cap at ~20 claims to keep prompt size reasonable
        claim_texts = claim_texts[:20]
        
        # Format numbered claims
        numbered = "\n".join(
            f"[{i}] {text}" for i, text in enumerate(claim_texts)
        )
        
        prompt = BATCH_CONTRADICTION_PROMPT.format(claims=numbered)
        
        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                system="You are a logical analysis assistant. Always respond with valid JSON."
            )
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            
            contradictions = []
            for c in result.get("contradictions", []):
                idx1 = c.get("claim1_index", 0)
                idx2 = c.get("claim2_index", 1)
                if 0 <= idx1 < len(claim_texts) and 0 <= idx2 < len(claim_texts):
                    contradictions.append({
                        "claim1": claim_texts[idx1],
                        "claim2": claim_texts[idx2],
                        "severity": c.get("severity", "minor"),
                        "explanation": c.get("explanation", ""),
                    })
            
            return contradictions
            
        except Exception as e:
            logger.warning(f"Batch contradiction detection failed: {e}")
            return []
    
    async def _assess_reliability(self, task: TaskAssignment) -> TaskResult:
        """
        Assess the overall reliability of sources.
        
        Args:
            task: Task with sources to assess
            
        Returns:
            Reliability assessment
        """
        sources = task.inputs.get("sources", [])
        
        assessments = []
        
        for source in sources:
            url = source.get("url", "")
            content = source.get("content", source.get("snippet", ""))
            
            # Domain-based scoring
            domain_score = self._score_domain(url)
            
            # Content quality scoring (placeholder for more sophisticated analysis)
            content_score = min(1.0, len(content) / 1000) * 0.5 + 0.5
            
            overall_score = (domain_score * 0.6 + content_score * 0.4)
            
            assessments.append({
                "url": url,
                "domain_score": domain_score,
                "content_score": content_score,
                "overall_score": overall_score,
                "is_reliable": overall_score >= 0.5
            })
        
        avg_reliability = (
            sum(a["overall_score"] for a in assessments) / len(assessments)
            if assessments else 0.5
        )
        
        return TaskResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="success",
            outputs={
                "assessments": assessments,
                "average_reliability": avg_reliability,
                "reliable_count": len([a for a in assessments if a["is_reliable"]])
            },
            confidence=avg_reliability
        )
    
    def _format_sources(self, sources: list[dict]) -> str:
        """Format sources for prompt context."""
        formatted = []
        
        for i, source in enumerate(sources[:10], 1):
            url = source.get("url", "Unknown URL")
            title = source.get("title", "No title")
            content = source.get("content", source.get("snippet", "No content"))
            
            # Truncate content
            if len(content) > 500:
                content = content[:500] + "..."
            
            formatted.append(f"[{i}] {title}\nURL: {url}\nContent: {content}\n")
        
        return "\n".join(formatted)
    
    def _calculate_reliability(self, verified_claims: list[dict]) -> float:
        """Calculate overall reliability score from verified claims."""
        if not verified_claims:
            return 0.5
        
        total_confidence = sum(
            c.get("confidence", 0.5)
            for c in verified_claims
        )
        
        # Weight by verification status
        status_weights = {
            "verified": 1.0,
            "disputed": 0.5,
            "refuted": 0.2,
            "unverified": 0.4
        }
        
        weighted_sum = sum(
            c.get("confidence", 0.5) * status_weights.get(c.get("status", "unverified"), 0.5)
            for c in verified_claims
        )
        
        return weighted_sum / len(verified_claims)
    
    def _score_domain(self, url: str) -> float:
        """Score domain reliability based on known patterns."""
        from urllib.parse import urlparse
        
        try:
            domain = urlparse(url).netloc.lower()
        except Exception:
            return 0.5
        
        # High reliability domains
        if any(d in domain for d in [".gov", ".edu", "nature.com", "science.org"]):
            return 0.95
        
        # Academic/research domains
        if any(d in domain for d in ["arxiv.org", "pubmed", "scholar.google"]):
            return 0.9
        
        # Reputable news/reference
        if any(d in domain for d in ["wikipedia.org", "bbc.com", "reuters.com", "apnews.com"]):
            return 0.8
        
        # Tech documentation
        if any(d in domain for d in ["docs.python.org", "developer.mozilla.org", "microsoft.com/docs"]):
            return 0.85
        
        # Stack Overflow / GitHub
        if any(d in domain for d in ["stackoverflow.com", "github.com"]):
            return 0.75
        
        # General .org
        if ".org" in domain:
            return 0.7
        
        # General .com
        if ".com" in domain:
            return 0.5
        
        return 0.5
    
    async def verify_answer(
        self,
        answer: str,
        sources: list[dict]
    ) -> dict[str, Any]:
        """
        Convenience method to verify an answer against sources.
        
        Args:
            answer: The answer to verify
            sources: Sources used to generate the answer
            
        Returns:
            Verification result
        """
        # Extract claims from answer
        # For now, split by sentences as a simple approach
        sentences = [s.strip() for s in answer.replace("\n", " ").split(".") if s.strip()]
        claims = [{"text": s} for s in sentences if len(s) > 20]
        
        task = TaskAssignment(
            task_type=TaskType.VERIFY_CLAIMS,
            agent_type="verifier",
            inputs={"claims": claims, "sources": sources}
        )
        
        result = await self.execute(task)
        return result.outputs
