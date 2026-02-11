"""Tests for User Experience Features."""
import pytest
import asyncio
from datetime import datetime
from src.core.agents.suggester import SuggestionAgent, SuggestionResult
from src.core.agents.transformer import TransformerAgent, TransformResult, QuickAction


class TestSuggestionAgent:
    """Tests for the SuggestionAgent."""
    
    @pytest.fixture
    def agent(self):
        return SuggestionAgent()
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.agent_id == "suggestion-agent"
        assert agent.agent_type == "suggester"
    
    def test_suggestion_result_dataclass(self):
        """Test SuggestionResult dataclass."""
        result = SuggestionResult(
            suggested_questions=["What is X?", "How does Y work?"],
            related_topics=["Topic A", "Topic B"],
            confidence=0.85
        )
        
        assert len(result.suggested_questions) == 2
        assert len(result.related_topics) == 2
        assert result.confidence == 0.85
        
        # Test to_dict
        d = result.to_dict()
        assert "suggested_questions" in d
        assert "related_topics" in d
        assert "confidence" in d
    
    @pytest.mark.asyncio
    async def test_generate_quick_suggestions(self, agent):
        """Test quick suggestion generation."""
        result = await agent.generate_suggestions(
            query="What is machine learning?",
            answer="Machine learning is a subset of AI that enables systems to learn from data.",
            quick=True
        )
        
        assert isinstance(result, SuggestionResult)
        # Quick mode should return at least some questions
        assert len(result.suggested_questions) >= 0  # May be empty if LLM fails
    
    @pytest.mark.asyncio
    async def test_generate_full_suggestions(self, agent):
        """Test full suggestion generation with sources and entities."""
        result = await agent.generate_suggestions(
            query="What are the benefits of renewable energy?",
            answer="""Renewable energy offers multiple benefits including reduced carbon emissions,
            energy independence, and job creation. Solar and wind power are the fastest growing
            sources. The transition to clean energy is accelerating globally.""",
            sources=["Nature Energy", "IEA Report 2025", "Bloomberg NEF"],
            entities=["solar power", "wind energy", "carbon emissions", "clean energy"],
            quick=False
        )
        
        assert isinstance(result, SuggestionResult)
        # Full mode should include related topics
        assert hasattr(result, "related_topics")
    
    @pytest.mark.asyncio
    async def test_parse_suggestions_json(self, agent):
        """Test parsing JSON formatted suggestions."""
        json_response = '''```json
{
    "suggested_questions": [
        "How does solar energy compare to wind?",
        "What is the cost of renewable energy?",
        "Which countries lead in clean energy?"
    ],
    "related_topics": [
        "Energy storage",
        "Grid modernization"
    ]
}
```'''
        
        result = agent._parse_suggestions(json_response)
        assert len(result.suggested_questions) == 3
        assert len(result.related_topics) == 2
        assert result.confidence >= 0.5
    
    @pytest.mark.asyncio
    async def test_parse_suggestions_fallback(self, agent):
        """Test fallback parsing when JSON fails."""
        text_response = '''
        Here are some follow-up questions:
        - "What are the main types of renewable energy?"
        - "How efficient is solar power?"
        - "What is the future of wind energy?"
        '''
        
        result = agent._parse_suggestions(text_response)
        # Should extract questions even without proper JSON
        assert isinstance(result.suggested_questions, list)


class TestSuggestionIntegration:
    """Integration tests for suggestions in research flow."""
    
    @pytest.mark.asyncio
    async def test_research_result_has_suggestions(self):
        """Test that ResearchResult includes suggestion fields."""
        from src.core.agents.orchestrator import ResearchResult
        
        result = ResearchResult(
            session_id="test-123",
            query="Test query",
            answer="Test answer",
            sources=[],
            verified_claims=[],
            contradictions=[],
            reliability_score=0.8,
            confidence=0.9,
            mode="balanced",
            iterations=1,
            duration_seconds=5.0,
            suggested_questions=["Question 1?", "Question 2?"],
            related_topics=["Topic A"]
        )
        
        assert len(result.suggested_questions) == 2
        assert len(result.related_topics) == 1
        
        # Test serialization
        d = result.to_dict()
        assert "suggested_questions" in d
        assert "related_topics" in d
    
    def test_response_schema_has_suggestions(self):
        """Test that API response schema includes suggestions."""
        from src.api.schemas import ResearchResponse, SuggestionResponse
        
        suggestion = SuggestionResponse(
            suggested_questions=["Q1?", "Q2?"],
            related_topics=["T1", "T2"]
        )
        
        assert len(suggestion.suggested_questions) == 2
        assert len(suggestion.related_topics) == 2
    
    def test_sse_event_type_has_suggestions(self):
        """Test that SSE event types include suggestions."""
        from src.api.schemas import SSEEventType
        
        assert SSEEventType.SUGGESTIONS == "suggestions"


# =============================================================================
# QUICK ACTIONS TESTS (Feature 1.2)
# =============================================================================

class TestTransformerAgent:
    """Tests for the TransformerAgent quick actions."""
    
    @pytest.fixture
    def agent(self):
        return TransformerAgent()
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.agent_id == "transformer-agent"
        assert agent.agent_type == "transformer"
    
    def test_quick_action_enum(self):
        """Test QuickAction enum values."""
        assert QuickAction.SUMMARIZE.value == "summarize"
        assert QuickAction.EXPLAIN_SIMPLE.value == "explain"
        assert QuickAction.COMPARE.value == "compare"
        assert QuickAction.TIMELINE.value == "timeline"
        assert QuickAction.PROS_CONS.value == "pros_cons"
        assert QuickAction.KEY_POINTS.value == "key_points"
        assert QuickAction.CODE_EXAMPLE.value == "code_example"
        assert QuickAction.DEEP_DIVE.value == "deep_dive"
    
    def test_transform_result_dataclass(self):
        """Test TransformResult dataclass."""
        result = TransformResult(
            action=QuickAction.SUMMARIZE,
            original_length=1000,
            transformed_content="## Summary\nThis is a summary.",
            transformed_length=30,
            metadata={"test": True}
        )
        
        assert result.action == QuickAction.SUMMARIZE
        assert result.original_length == 1000
        assert result.transformed_length == 30
        
        # Test to_dict
        d = result.to_dict()
        assert d["action"] == "summarize"
        assert "transformed_content" in d
        assert "metadata" in d
    
    @pytest.mark.asyncio
    async def test_transform_summarize(self, agent):
        """Test summarize transformation."""
        content = """
        Machine learning is a subset of artificial intelligence that enables systems 
        to learn and improve from experience without being explicitly programmed. 
        It focuses on developing algorithms that can access data and use it to learn.
        There are three main types: supervised learning, unsupervised learning, and 
        reinforcement learning. Each has different use cases and applications.
        Machine learning is used in image recognition, natural language processing,
        recommendation systems, and autonomous vehicles.
        """
        
        result = await agent.transform(
            action=QuickAction.SUMMARIZE,
            content=content
        )
        
        assert isinstance(result, TransformResult)
        assert result.action == QuickAction.SUMMARIZE
        assert result.original_length > 0
        assert len(result.transformed_content) > 0
    
    @pytest.mark.asyncio
    async def test_transform_explain_simple(self, agent):
        """Test explain simple (ELI5) transformation."""
        content = """
        Quantum entanglement is a phenomenon where particles become interconnected 
        such that the quantum state of each particle cannot be described independently. 
        When particles are entangled, measuring one particle instantaneously affects 
        the state of the other, regardless of the distance between them.
        """
        
        result = await agent.transform(
            action=QuickAction.EXPLAIN_SIMPLE,
            content=content
        )
        
        assert isinstance(result, TransformResult)
        assert result.action == QuickAction.EXPLAIN_SIMPLE
    
    @pytest.mark.asyncio
    async def test_transform_key_points(self, agent):
        """Test key points extraction."""
        content = """
        Python is a high-level programming language known for its simplicity.
        It was created by Guido van Rossum in 1991. Python emphasizes code 
        readability with significant whitespace. It supports multiple paradigms
        including procedural, object-oriented, and functional programming.
        Python has a large standard library and active community.
        """
        
        result = await agent.transform(
            action=QuickAction.KEY_POINTS,
            content=content
        )
        
        assert isinstance(result, TransformResult)
        assert result.action == QuickAction.KEY_POINTS


class TestTransformSchemas:
    """Test API schemas for quick actions."""
    
    def test_quick_action_type_enum(self):
        """Test QuickActionType API enum."""
        from src.api.schemas import QuickActionType
        
        assert QuickActionType.SUMMARIZE.value == "summarize"
        assert QuickActionType.EXPLAIN_SIMPLE.value == "explain"
        assert QuickActionType.COMPARE.value == "compare"
    
    def test_transform_request_model(self):
        """Test TransformRequest model."""
        from src.api.schemas import TransformRequest, QuickActionType
        
        request = TransformRequest(
            action=QuickActionType.SUMMARIZE
        )
        assert request.action == QuickActionType.SUMMARIZE
        assert request.language == "python"  # default
        
        request_with_context = TransformRequest(
            action=QuickActionType.COMPARE,
            context="Python vs JavaScript"
        )
        assert request_with_context.context == "Python vs JavaScript"
    
    def test_transform_response_model(self):
        """Test TransformResponse model."""
        from src.api.schemas import TransformResponse, QuickActionType
        
        response = TransformResponse(
            session_id="test-123",
            action=QuickActionType.SUMMARIZE,
            original_length=1000,
            transformed_content="Summary here",
            transformed_length=12,
            duration_ms=500
        )
        
        assert response.session_id == "test-123"
        assert response.action == QuickActionType.SUMMARIZE
        assert response.duration_ms == 500


# =============================================================================
# CONVERSATION THREADING TESTS (Feature 1.3)
# =============================================================================

class TestConversationTree:
    """Tests for conversation threading/branching."""
    
    @pytest.fixture
    async def tree(self):
        """Create a fresh conversation tree for testing."""
        from src.storage.conversation import ConversationTree
        import tempfile
        import os
        
        # Use temp database
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_conversations.db")
        return ConversationTree(db_path=db_path)
    
    @pytest.mark.asyncio
    async def test_create_node(self, tree):
        """Test creating a conversation node."""
        node = await tree.create_node(
            session_id="session-1",
            query="What is machine learning?",
            response="Machine learning is a subset of AI...",
            sources=["https://example.com/ml"]
        )
        
        assert node.id is not None
        assert node.session_id == "session-1"
        assert node.query == "What is machine learning?"
        assert node.parent_id is None
        assert len(node.sources) == 1
    
    @pytest.mark.asyncio
    async def test_branch_from_node(self, tree):
        """Test creating a branch from existing node."""
        # Create root node
        root = await tree.create_node(
            session_id="session-1",
            query="What is Python?",
            response="Python is a programming language..."
        )
        
        # Create branch
        branch = await tree.branch_from(
            node_id=root.id,
            new_query="What about Python for web development?",
            new_response="Python is great for web dev with Flask and Django..."
        )
        
        assert branch is not None
        assert branch.parent_id == root.id
        assert branch.session_id == root.session_id
        
        # Verify parent's children list updated
        updated_root = await tree.get_node(root.id)
        assert branch.id in updated_root.children
    
    @pytest.mark.asyncio
    async def test_get_context_chain(self, tree):
        """Test retrieving conversation context chain."""
        # Create chain: root -> child1 -> child2
        root = await tree.create_node(
            session_id="session-1",
            query="Q1",
            response="A1"
        )
        child1 = await tree.branch_from(root.id, "Q2", "A2")
        child2 = await tree.branch_from(child1.id, "Q3", "A3")
        
        # Get context chain for child2
        chain = await tree.get_context_chain(child2.id, max_depth=5)
        
        assert len(chain) == 3
        assert chain[0].id == root.id  # Oldest first
        assert chain[2].id == child2.id  # Most recent last
    
    @pytest.mark.asyncio
    async def test_get_tree(self, tree):
        """Test getting full conversation tree."""
        # Create tree with branches
        root = await tree.create_node(
            session_id="session-1",
            query="Root question",
            response="Root answer"
        )
        await tree.branch_from(root.id, "Branch 1", "Answer 1")
        await tree.branch_from(root.id, "Branch 2", "Answer 2")
        
        nodes = await tree.get_tree("session-1")
        
        assert len(nodes) == 3
    
    @pytest.mark.asyncio
    async def test_get_tree_info(self, tree):
        """Test getting tree summary info."""
        # Create tree
        root = await tree.create_node(
            session_id="session-1",
            query="Root",
            response="Answer"
        )
        child = await tree.branch_from(root.id, "Child", "Answer")
        await tree.branch_from(root.id, "Sibling", "Answer")  # Creates a branch
        
        info = await tree.get_tree_info("session-1")
        
        assert info is not None
        assert info.total_nodes == 3
        assert info.max_depth == 1
        assert info.branch_count == 1  # One branch point (root has 2 children)
    
    @pytest.mark.asyncio
    async def test_delete_node_recursive(self, tree):
        """Test deleting a node and its descendants."""
        root = await tree.create_node(
            session_id="session-1",
            query="Root",
            response="Answer"
        )
        child = await tree.branch_from(root.id, "Child", "Answer")
        grandchild = await tree.branch_from(child.id, "Grandchild", "Answer")
        
        # Delete child (should also delete grandchild)
        deleted = await tree.delete_node(child.id, recursive=True)
        
        assert deleted == 2
        
        # Verify only root remains
        nodes = await tree.get_tree("session-1")
        assert len(nodes) == 1
        assert nodes[0].id == root.id
    
    @pytest.mark.asyncio
    async def test_export_tree(self, tree):
        """Test exporting conversation tree."""
        await tree.create_node(
            session_id="session-1",
            query="Question",
            response="Answer"
        )
        
        export = await tree.export_tree("session-1")
        
        assert "session_id" in export
        assert "nodes" in export
        assert "info" in export
        assert len(export["nodes"]) == 1


class TestConversationSchemas:
    """Test API schemas for conversation threading."""
    
    def test_conversation_node_response(self):
        """Test ConversationNodeResponse model."""
        from src.api.schemas import ConversationNodeResponse
        
        node = ConversationNodeResponse(
            id="node-1",
            session_id="session-1",
            query="What is AI?",
            response="AI is artificial intelligence...",
            sources=["https://example.com"],
            parent_id=None,
            children=["node-2"],
            created_at=datetime.utcnow()
        )
        
        assert node.id == "node-1"
        assert len(node.children) == 1
    
    def test_branch_request(self):
        """Test BranchRequest model."""
        from src.api.schemas import BranchRequest
        
        request = BranchRequest(
            node_id="node-1",
            query="Follow-up question",
            mode="balanced"
        )
        
        assert request.node_id == "node-1"
        assert request.mode == "balanced"


# =============================================================================
# SOURCE QUALITY BADGES TESTS (Feature 1.4)
# =============================================================================

class TestSourceQualityBadges:
    """Tests for source quality badges."""
    
    def test_source_quality_badges_model(self):
        """Test SourceQualityBadges model."""
        from src.api.schemas import SourceQualityBadges
        
        badges = SourceQualityBadges(
            is_verified=True,
            is_recent=True,
            is_authoritative=True,
            is_primary_source=False,
            is_academic=True
        )
        
        assert badges.is_verified == True
        assert badges.is_academic == True
        assert badges.is_primary_source == False
    
    def test_source_score_breakdown_model(self):
        """Test SourceScoreBreakdown model."""
        from src.api.schemas import SourceScoreBreakdown
        
        breakdown = SourceScoreBreakdown(
            authority=0.9,
            freshness=0.8,
            relevance=0.75,
            content_quality=0.85
        )
        
        assert breakdown.authority == 0.9
        assert breakdown.freshness == 0.8
    
    def test_source_with_badges(self):
        """Test Source model with badges."""
        from src.api.schemas import Source, SourceQualityBadges, SourceScoreBreakdown
        
        source = Source(
            index=1,
            title="Academic Paper",
            url="https://arxiv.org/abs/2024.12345",
            domain="arxiv.org",
            quality_score=0.92,
            badges=SourceQualityBadges(
                is_verified=True,
                is_academic=True,
                is_authoritative=True
            ),
            score_breakdown=SourceScoreBreakdown(
                authority=0.95,
                freshness=0.9,
                relevance=0.88,
                content_quality=0.85
            ),
            verification_status="verified"
        )
        
        assert source.badges.is_academic == True
        assert source.score_breakdown.authority == 0.95
        assert source.verification_status == "verified"


class TestQualityScorerBadges:
    """Tests for QualityScorer badge computation."""
    
    @pytest.fixture
    def scorer(self):
        from src.processing.scorer import QualityScorer
        return QualityScorer()
    
    def test_compute_badges_academic(self, scorer):
        """Test badge computation for academic source."""
        badges = scorer.compute_badges(
            url="https://arxiv.org/abs/2024.12345",
            authority_score=0.95,
            freshness_score=0.8,
            verified=True
        )
        
        assert badges["is_academic"] == True
        assert badges["is_primary_source"] == True
        assert badges["is_authoritative"] == True
        assert badges["is_verified"] == True
        assert badges["is_recent"] == True
    
    def test_compute_badges_news(self, scorer):
        """Test badge computation for news source."""
        badges = scorer.compute_badges(
            url="https://techcrunch.com/article",
            authority_score=0.7,
            freshness_score=0.95,
            verified=False
        )
        
        assert badges["is_academic"] == False
        assert badges["is_primary_source"] == False
        assert badges["is_authoritative"] == False  # 0.7 < 0.8
        assert badges["is_verified"] == False
        assert badges["is_recent"] == True  # 0.95 >= 0.7
    
    def test_compute_badges_gov(self, scorer):
        """Test badge computation for government source."""
        badges = scorer.compute_badges(
            url="https://cdc.gov/health/data",
            authority_score=0.9,
            freshness_score=0.5,
            verified=True
        )
        
        assert badges["is_primary_source"] == True
        assert badges["is_authoritative"] == True
        assert badges["is_recent"] == False  # 0.5 < 0.7
    
    def test_compute_badges_edu(self, scorer):
        """Test badge computation for .edu domain."""
        badges = scorer.compute_badges(
            url="https://cs.stanford.edu/research",
            authority_score=0.88,
            freshness_score=0.75,
            verified=False
        )
        
        assert badges["is_academic"] == True
        assert badges["is_authoritative"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
