"""
Relationship Types and Models.

Defines the types of relationships that can connect entities in the knowledge graph.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import uuid


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    
    # Professional/Organizational
    WORKS_AT = "works_at"
    FOUNDED = "founded"
    LEADS = "leads"
    MEMBER_OF = "member_of"
    AFFILIATED_WITH = "affiliated_with"
    
    # Creation/Authorship
    AUTHORED = "authored"
    CREATED = "created"
    DEVELOPED = "developed"
    INVENTED = "invented"
    PUBLISHED = "published"
    
    # Research/Academic
    CITES = "cites"
    REFERENCES = "references"
    BUILDS_ON = "builds_on"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    REPLICATES = "replicates"
    
    # Technical
    USES = "uses"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    DEPENDS_ON = "depends_on"
    COMPATIBLE_WITH = "compatible_with"
    ALTERNATIVE_TO = "alternative_to"
    
    # Conceptual
    IS_A = "is_a"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    DERIVED_FROM = "derived_from"
    ENABLES = "enables"
    
    # Temporal
    PRECEDED_BY = "preceded_by"
    FOLLOWED_BY = "followed_by"
    CONCURRENT_WITH = "concurrent_with"
    
    # Quantitative
    MEASURED_BY = "measured_by"
    OUTPERFORMS = "outperforms"
    COMPARABLE_TO = "comparable_to"
    
    # Location/Geographic
    LOCATED_IN = "located_in"
    OCCURRED_AT = "occurred_at"
    
    # Generic
    ASSOCIATED_WITH = "associated_with"
    MENTIONED_IN = "mentioned_in"


@dataclass
class Relationship:
    """
    Represents a relationship between two entities.
    
    Relationships are the edges in the knowledge graph,
    connecting source entities to target entities.
    """
    
    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    bidirectional: bool = False
    evidence: str = ""  # Text that supports this relationship
    source_document: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType | str,
        evidence: str = "",
        **kwargs
    ) -> "Relationship":
        """
        Factory method to create a relationship.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            evidence: Supporting text
            **kwargs: Additional properties
            
        Returns:
            New Relationship instance
        """
        if isinstance(relationship_type, str):
            relationship_type = RelationshipType(relationship_type.lower())
        
        rel_id = f"rel_{uuid.uuid4().hex[:12]}"
        
        return cls(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=kwargs.get("properties", {}),
            weight=kwargs.get("weight", 1.0),
            bidirectional=kwargs.get("bidirectional", False),
            evidence=evidence,
            source_document=kwargs.get("source_document"),
            confidence=kwargs.get("confidence", 1.0)
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "properties": self.properties,
            "weight": self.weight,
            "bidirectional": self.bidirectional,
            "evidence": self.evidence,
            "source_document": self.source_document,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Relationship":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship_type=RelationshipType(data["relationship_type"]),
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            bidirectional=data.get("bidirectional", False),
            evidence=data.get("evidence", ""),
            source_document=data.get("source_document"),
            confidence=data.get("confidence", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow()
        )
    
    def reverse(self) -> "Relationship":
        """
        Create a reversed relationship (swap source and target).
        
        Useful for bidirectional relationships.
        
        Returns:
            New Relationship with source and target swapped
        """
        return Relationship(
            id=f"{self.id}_rev",
            source_id=self.target_id,
            target_id=self.source_id,
            relationship_type=self._get_reverse_type(),
            properties=self.properties,
            weight=self.weight,
            bidirectional=self.bidirectional,
            evidence=self.evidence,
            source_document=self.source_document,
            confidence=self.confidence,
            created_at=self.created_at
        )
    
    def _get_reverse_type(self) -> RelationshipType:
        """Get the reverse relationship type if applicable."""
        reverse_map = {
            RelationshipType.PRECEDED_BY: RelationshipType.FOLLOWED_BY,
            RelationshipType.FOLLOWED_BY: RelationshipType.PRECEDED_BY,
            RelationshipType.LEADS: RelationshipType.MEMBER_OF,
            RelationshipType.AUTHORED: RelationshipType.AUTHORED,  # Keep same
            RelationshipType.CITES: RelationshipType.CITED_BY if hasattr(RelationshipType, 'CITED_BY') else RelationshipType.CITES,
        }
        return reverse_map.get(self.relationship_type, self.relationship_type)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, Relationship):
            return False
        return self.id == other.id


# Common relationship patterns for entity extraction
RELATIONSHIP_PATTERNS = {
    "works_at": ["works at", "employed by", "works for", "employee of"],
    "founded": ["founded", "co-founded", "started", "established"],
    "authored": ["authored", "wrote", "published", "written by"],
    "uses": ["uses", "utilizes", "employs", "leverages"],
    "related_to": ["related to", "connected to", "associated with"],
    "is_a": ["is a", "is an", "type of", "kind of"],
    "part_of": ["part of", "component of", "belongs to", "included in"],
}
