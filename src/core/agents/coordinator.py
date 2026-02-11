"""
Coordinator Agent.

Master agent that orchestrates the research process by:
- Decomposing queries into tasks
- Assigning tasks to specialized agents
- Aggregating and synthesizing results
- Managing the research workflow
"""

import asyncio
import json
import time
from typing import Any, Optional
from dataclasses import dataclass, field

from src.utils.logging import get_logger
from src.core.agents.base import (
    BaseAgent,
    AgentCapability,
    AgentPool,
)
from src.core.agents.protocol import (
    TaskAssignment,
    TaskResult,
    TaskType,
    Priority,
    ResearchPlan,
)
from src.core.agent.modes import SearchMode, MODE_CONFIGS, ModeConfig
from src.services.llm.ollama import OllamaService
from src.config import get_settings


logger = get_logger(__name__)


# Prompts for the coordinator
PLANNING_PROMPT = """You are a research planning expert. Analyze this query and create a comprehensive research plan.

Query: {query}
Research Mode: {mode} (time budget: {time_budget}s)
Available Agents: {agents}

Create a plan with:
1. The user's intent/goal
2. 2-5 sub-queries that cover different aspects
3. Source types to search (web, academic, code, news)
4. Key concepts to focus on
5. Verification level needed (minimal, standard, rigorous)
6. Output format preference (prose, bullets, structured)

Respond in JSON format:
{{
    "intent": "Clear description of what user wants to know",
    "sub_queries": ["query1", "query2", ...],
    "source_types": ["web", "academic", ...],
    "strategies": ["general", "focused", ...],
    "key_concepts": ["concept1", "concept2", ...],
    "verification_level": "standard",
    "output_format": "prose"
}}
"""


@dataclass
class ResearchContext:
    """Context for a research session."""
    query: str
    session_id: str
    mode: SearchMode
    mode_config: ModeConfig
    plan: Optional[ResearchPlan] = None
    start_time: float = field(default_factory=time.time)
    
    # User context from memories
    user_context: str = ""
    
    # Results from various phases
    search_results: list[dict] = field(default_factory=list)
    crawl_results: list[dict] = field(default_factory=list)
    processed_content: list[dict] = field(default_factory=list)
    verified_claims: list[dict] = field(default_factory=list)
    knowledge_entities: list[dict] = field(default_factory=list)
    knowledge_relationships: list[dict] = field(default_factory=list)
    
    # Final outputs
    draft_answer: str = ""
    final_answer: str = ""
    sources: list[dict] = field(default_factory=list)
    
    # Tracking
    errors: list[dict] = field(default_factory=list)
    timing: dict[str, float] = field(default_factory=dict)
    iteration: int = 0
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def time_remaining(self) -> float:
        """Get remaining time budget."""
        return max(0, self.mode_config.crawl_timeout * 2 - self.elapsed_time)
    
    def to_state(self) -> dict[str, Any]:
        """Convert to state dictionary for compatibility."""
        return {
            "query": self.query,
            "session_id": self.session_id,
            "mode": self.mode,
            "mode_config": self.mode_config,
            "research_plan": self.plan.to_dict() if self.plan else {},
            "sub_queries": self.plan.sub_queries if self.plan else [],
            "search_results": self.search_results,
            "crawl_results": self.crawl_results,
            "processed_documents": self.processed_content,
            "verified_claims": self.verified_claims,
            "knowledge_entities": self.knowledge_entities,
            "knowledge_relationships": self.knowledge_relationships,
            "draft_answer": self.draft_answer,
            "final_answer": self.final_answer,
            "answer_with_citations": self.final_answer,
            "sources": self.sources,
            "errors": self.errors,
            "timing": self.timing,
            "iteration_count": self.iteration,
        }


class CoordinatorAgent(BaseAgent):
    """
    Coordinator agent that orchestrates the research workflow.
    
    Responsibilities:
    - Create research plans from user queries
    - Delegate tasks to specialized agents
    - Aggregate results from multiple agents
    - Manage iteration and quality control
    - Handle errors and fallbacks
    """
    
    def __init__(
        self,
        agent_pool: Optional[AgentPool] = None,
        llm_service: Optional[OllamaService] = None,
    ):
        """
        Initialize the coordinator.
        
        Args:
            agent_pool: Pool of worker agents
            llm_service: LLM service for planning
        """
        super().__init__(
            agent_type="coordinator",
            capabilities=[AgentCapability.COORDINATION, AgentCapability.PLANNING]
        )
        
        self.agent_pool = agent_pool or AgentPool()
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
                default_model=self.settings.llm.models.planner,
                timeout=self.settings.llm.timeout
            )
        return self._llm_service
    
    async def execute(self, task: TaskAssignment) -> TaskResult:
        """
        Execute a coordination task.
        
        The coordinator handles high-level research orchestration.
        """
        task_type = task.task_type
        
        if task_type == TaskType.CREATE_PLAN:
            return await self._create_plan(task)
        else:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[f"Unknown task type for coordinator: {task_type}"]
            )
    
    async def research(
        self,
        query: str,
        session_id: str,
        mode: SearchMode = SearchMode.BALANCED,
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute a complete research workflow.
        
        This is the main entry point for research.
        
        Args:
            query: The research query
            session_id: Session ID for tracking
            mode: Research mode
            context: Optional user context (from memories or explicit context)
            
        Returns:
            Final research state
        """
        mode_config = MODE_CONFIGS[mode]
        research_ctx = ResearchContext(
            query=query,
            session_id=session_id,
            mode=mode,
            mode_config=mode_config
        )
        
        # Store user context for synthesis phase
        if context:
            research_ctx.user_context = context
            logger.debug(f"Research context includes user memory/context ({len(context)} chars)")
        
        logger.info(f"Starting coordinated research: {query[:80]}... (mode: {mode.value})")
        
        try:
            # Phase 1: Planning (skip if disabled for speed)
            if mode_config.enable_planning:
                await self._phase_planning(research_ctx)
            else:
                # Quick fallback - no LLM call
                research_ctx.plan = ResearchPlan(
                    query=query,
                    intent=query,
                    sub_queries=[query],  # Just use original query
                    source_types=["web"],
                    strategies=["general"]
                )
                logger.debug("Skipping LLM planning for quick mode")
            
            # Phase 2: Research (search + crawl)
            await self._phase_research(research_ctx)
            
            # Phase 3: Processing
            await self._phase_processing(research_ctx)
            
            # Phase 4: Verification (only if enabled)
            if mode_config.enable_verification:
                await self._phase_verification(research_ctx)
            else:
                logger.debug("Skipping verification phase")
            
            # Phase 5: Synthesis
            await self._phase_synthesis(research_ctx)
            
            # Phase 6: Review and iteration (only if enabled AND has iterations)
            if mode_config.enable_reflection and mode_config.max_iterations > 0:
                while (
                    research_ctx.iteration < mode_config.max_iterations
                    and research_ctx.time_remaining > 30
                ):
                    needs_more = await self._phase_review(research_ctx)
                    if not needs_more:
                        break
                    
                    research_ctx.iteration += 1
                    logger.info(f"Starting iteration {research_ctx.iteration}")
                    
                    # Do more research
                    await self._phase_research(research_ctx)
                    await self._phase_processing(research_ctx)
                    await self._phase_synthesis(research_ctx)
            
            logger.info(f"Research complete in {research_ctx.elapsed_time:.1f}s")
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            research_ctx.errors.append({
                "phase": "coordination",
                "error": str(e)
            })
        
        return research_ctx.to_state()
    
    async def _phase_planning(self, context: ResearchContext):
        """Execute the planning phase."""
        start = time.time()
        logger.info("Phase: Planning")
        
        try:
            # Create research plan using LLM
            plan = await self._create_research_plan(context)
            context.plan = plan
            
        except Exception as e:
            logger.warning(f"Planning failed, using fallback: {e}")
            # Fallback plan
            context.plan = ResearchPlan(
                query=context.query,
                intent=context.query,
                sub_queries=[context.query],
                source_types=["web"],
                strategies=["general"]
            )
        
        context.timing["planning"] = time.time() - start
    
    async def _phase_research(self, context: ResearchContext):
        """Execute the research phase (search + crawl)."""
        start = time.time()
        logger.info("Phase: Research")
        
        # Get researcher agent
        researcher = self.agent_pool.get_agent("researcher")
        
        if researcher is None:
            logger.warning("No researcher agent available, using fallback")
            # Will be handled by the graph-based system
            context.timing["research"] = time.time() - start
            return
        
        # Execute search task
        search_task = TaskAssignment(
            task_type=TaskType.WEB_SEARCH,
            agent_type="researcher",
            inputs={
                "queries": context.plan.sub_queries if context.plan else [context.query],
                "num_results": context.mode_config.max_search_results,
                "source_types": context.plan.source_types if context.plan else ["web"]
            },
            priority=Priority.HIGH,
            timeout=30.0
        )
        
        search_result = await researcher.execute_with_tracking(search_task)
        
        if search_result.is_success or search_result.is_partial:
            context.search_results = search_result.outputs.get("results", [])
            
            # Get URLs to crawl
            urls = [r.get("url") for r in context.search_results if r.get("url")]
            urls = urls[:context.mode_config.max_sources_to_crawl]
            
            # Execute crawl task
            crawl_task = TaskAssignment(
                task_type=TaskType.CRAWL_URLS,
                agent_type="researcher",
                inputs={
                    "urls": urls,
                    "timeout": context.mode_config.crawl_timeout
                },
                priority=Priority.HIGH,
                timeout=context.mode_config.crawl_timeout + 10
            )
            
            crawl_result = await researcher.execute_with_tracking(crawl_task)
            
            if crawl_result.is_success or crawl_result.is_partial:
                context.crawl_results = crawl_result.outputs.get("results", [])
        else:
            context.errors.append({
                "phase": "research",
                "error": search_result.errors
            })
        
        context.timing["research"] = time.time() - start
    
    async def _phase_processing(self, context: ResearchContext):
        """
        Execute the processing phase.
        
        Takes the crawled content and extracts structured facts,
        scores chunks for relevance, and builds the processed_content
        list that feeds verification and synthesis.
        """
        start = time.time()
        logger.info("Phase: Processing")
        
        if not context.crawl_results:
            logger.debug("No crawl results to process")
            context.timing["processing"] = time.time() - start
            return
        
        from src.processing.models import ContentChunk, ExtractedFact
        from src.processing.extractor import QuickFactExtractor
        from src.processing.scorer import QualityScorer
        
        fact_extractor = QuickFactExtractor()
        scorer = QualityScorer()
        
        crawl_data_list = context.crawl_results
        query = context.query

        def _process_all():
            """CPU-bound scoring + fact extraction — runs in executor."""
            _processed = []
            for crawl_data in crawl_data_list:
                url = crawl_data.get("url", "")
                title = crawl_data.get("title", "")
                content = crawl_data.get("content", "")
                chunk_texts = crawl_data.get("chunks", [])
                quality_score = crawl_data.get("quality_score", 0.5)
                
                if not chunk_texts:
                    continue
                
                # Reconstruct ContentChunk objects from text
                chunks = []
                for i, text in enumerate(chunk_texts):
                    chunk = ContentChunk(
                        id="",
                        source_url=url,
                        source_title=title,
                        content=text,
                        chunk_index=i,
                        total_chunks=len(chunk_texts),
                    )
                    chunk.relevance_score = scorer.score_relevance(text, query)
                    chunk.quality_score = quality_score
                    chunks.append(chunk)
                
                # Extract facts from all chunks
                facts = []
                for chunk in chunks:
                    chunk_facts = fact_extractor.extract_facts(chunk)
                    for fact in chunk_facts:
                        facts.append({
                            "fact": fact.content,
                            "source_url": url,
                            "source_title": title,
                            "confidence": fact.confidence,
                            "category": fact.category or "general",
                        })
                
                chunks.sort(key=lambda c: c.relevance_score, reverse=True)
                
                _processed.append({
                    "url": url,
                    "title": title,
                    "content": content,
                    "chunks": [c.content for c in chunks],
                    "facts": facts,
                    "quality_score": quality_score,
                    "chunk_count": len(chunks),
                    "fact_count": len(facts),
                })
            
            _processed.sort(key=lambda p: p.get("quality_score", 0), reverse=True)
            return _processed
        
        # Run CPU-bound processing off the event loop
        loop = asyncio.get_event_loop()
        processed = await loop.run_in_executor(None, _process_all)
        context.processed_content = processed
        
        total_facts = sum(p.get("fact_count", 0) for p in processed)
        logger.info(
            f"Processing complete: {len(processed)} documents, "
            f"{total_facts} facts extracted"
        )

        # --- Knowledge-graph entity extraction (best-effort) -----------------
        try:
            await self._extract_knowledge(context, processed)
        except Exception as e:
            logger.warning(f"Knowledge graph extraction skipped: {e}")
        
        context.timing["processing"] = time.time() - start
    
    async def _extract_knowledge(
        self, context: ResearchContext, processed: list[dict]
    ) -> None:
        """
        Run knowledge-graph entity & relationship extraction on processed
        content.

        Uses the top-3 documents (by quality) to avoid excessive LLM calls,
        and merges extracted entities/relationships into the context.
        """
        from src.knowledge.extraction import EntityExtractor

        top_docs = processed[:3]
        if not top_docs:
            return

        extractor = EntityExtractor(
            llm_service=self.llm_service,
            model=self.settings.llm.models.planner,
        )

        all_entities: list[dict] = []
        all_relationships: list[dict] = []
        seen_entity_names: set[str] = set()

        for doc in top_docs:
            # Combine chunks into a single text block (max ~4 000 chars each)
            text = "\n\n".join(doc.get("chunks", [])[:4])
            if not text.strip():
                continue

            result = await extractor.extract(
                text=text,
                context=context.query,
                generate_embeddings=False,
            )

            for ent in result.entities:
                key = ent.name.lower()
                if key not in seen_entity_names:
                    seen_entity_names.add(key)
                    all_entities.append({
                        "name": ent.name,
                        "type": ent.entity_type.value if hasattr(ent.entity_type, "value") else str(ent.entity_type),
                        "description": ent.description,
                    })

            for rel in result.relationships:
                all_relationships.append({
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type),
                })

        context.knowledge_entities = all_entities
        context.knowledge_relationships = all_relationships
        logger.info(
            f"Knowledge extraction: {len(all_entities)} entities, "
            f"{len(all_relationships)} relationships"
        )

    async def _phase_verification(self, context: ResearchContext):
        """Execute the verification phase."""
        start = time.time()
        logger.info("Phase: Verification")
        
        verifier = self.agent_pool.get_agent("verifier")
        
        if verifier is None:
            logger.debug("No verifier agent, skipping verification")
            context.timing["verification"] = time.time() - start
            return
        
        # Extract claims from processed content
        claims = []
        for content in context.processed_content:
            if "facts" in content:
                claims.extend(content["facts"])
        
        if claims:
            verify_task = TaskAssignment(
                task_type=TaskType.VERIFY_CLAIMS,
                agent_type="verifier",
                inputs={
                    "claims": claims[:20],  # Limit for performance
                    "sources": context.crawl_results
                },
                priority=Priority.NORMAL,
                timeout=60.0
            )
            
            verify_result = await verifier.execute_with_tracking(verify_task)
            
            if verify_result.is_success:
                context.verified_claims = verify_result.outputs.get("verified_claims", [])
        
        context.timing["verification"] = time.time() - start
    
    async def _phase_synthesis(self, context: ResearchContext):
        """Execute the synthesis phase."""
        start = time.time()
        logger.info("Phase: Synthesis")
        
        writer = self.agent_pool.get_agent("writer")
        
        if writer is None:
            logger.debug("No writer agent, using fallback synthesis")
            # Fallback to basic synthesis
            context.timing["synthesis"] = time.time() - start
            return
        
        synthesis_task = TaskAssignment(
            task_type=TaskType.SYNTHESIZE_ANSWER,
            agent_type="writer",
            inputs={
                "query": context.query,
                "content": context.processed_content,
                "verified_claims": context.verified_claims,
                "max_chunks": context.mode_config.max_chunks_for_synthesis
            },
            priority=Priority.HIGH,
            timeout=90.0
        )
        
        synthesis_result = await writer.execute_with_tracking(synthesis_task)
        
        if synthesis_result.is_success:
            context.draft_answer = synthesis_result.outputs.get("answer", "")
            context.final_answer = synthesis_result.outputs.get("answer_with_citations", "")
            context.sources = synthesis_result.outputs.get("sources", [])
        
        context.timing["synthesis"] = time.time() - start
    
    async def _phase_review(self, context: ResearchContext) -> bool:
        """
        Execute the review phase.
        
        Returns:
            True if more research is needed
        """
        start = time.time()
        logger.info("Phase: Review")
        
        # Check if we have enough quality content
        if not context.final_answer:
            context.timing["review"] = time.time() - start
            return True  # Need more research
        
        # For now, basic quality check
        word_count = len(context.final_answer.split())
        has_citations = "[" in context.final_answer and "]" in context.final_answer
        
        needs_more = word_count < 100 or not has_citations
        
        context.timing["review"] = time.time() - start
        return needs_more
    
    async def _create_research_plan(self, context: ResearchContext) -> ResearchPlan:
        """Create a research plan using LLM."""
        prompt = PLANNING_PROMPT.format(
            query=context.query,
            mode=context.mode.value,
            time_budget=context.mode_config.crawl_timeout * 2,
            agents=self.agent_pool.available_agents
        )
        
        response = await self.llm_service.generate(
            prompt=prompt,
            system="You are a research planning assistant. Always respond with valid JSON."
        )
        
        # Parse response
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            plan_data = json.loads(content.strip())
            plan_data["query"] = context.query
            
            return ResearchPlan.from_dict(plan_data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse plan: {e}")
            return ResearchPlan(
                query=context.query,
                intent=context.query,
                sub_queries=[context.query]
            )
    
    async def _create_plan(self, task: TaskAssignment) -> TaskResult:
        """Create a research plan (task handler)."""
        query = task.inputs.get("query", "")
        mode = task.inputs.get("mode", SearchMode.BALANCED)
        
        if isinstance(mode, str):
            mode = SearchMode(mode)
        
        mode_config = MODE_CONFIGS[mode]
        context = ResearchContext(
            query=query,
            session_id=task.inputs.get("session_id", ""),
            mode=mode,
            mode_config=mode_config
        )
        
        try:
            plan = await self._create_research_plan(context)
            
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="success",
                outputs={"plan": plan.to_dict()},
                confidence=0.9
            )
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status="failed",
                errors=[str(e)]
            )
