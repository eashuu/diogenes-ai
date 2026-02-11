"""
Entity Types and Models.

Defines the types of entities that can be extracted and stored in the knowledge graph.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import uuid


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""
    # People & Organizations
    PERSON = "person"
    ORGANIZATION = "organization"
    COMPANY = "company"
    INSTITUTION = "institution"
    
    # Concepts & Topics
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    METHODOLOGY = "methodology"
    THEORY = "theory"
    
    # Research & Academic
    RESEARCH_PAPER = "research_paper"
    DATASET = "dataset"
    EXPERIMENT = "experiment"
    FINDING = "finding"
    
    # Products & Artifacts
    PRODUCT = "product"
    SOFTWARE = "software"
    TOOL = "tool"
    
    # Locations & Time
    LOCATION = "location"
    EVENT = "event"
    TIME_PERIOD = "time_period"
    
    # Quantitative
    METRIC = "metric"
    STATISTIC = "statistic"
    
    # Other
    OTHER = "other"


@dataclass
class Entity:
    """
    Represents an entity in the knowledge graph.
    
    Entities are the nodes in the graph, representing people,
    organizations, concepts, technologies, etc.
    """
    
    id: str
    name: str
    entity_type: EntityType
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    embedding: Optional[list[float]] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(
        cls,
        name: str,
        entity_type: EntityType | str,
        description: str = "",
        **kwargs
    ) -> "Entity":
        """
        Factory method to create an entity with auto-generated ID.
        
        Args:
            name: Entity name
            entity_type: Type of entity
            description: Description of the entity
            **kwargs: Additional properties
            
        Returns:
            New Entity instance
        """
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type.lower())
        
        entity_id = f"ent_{uuid.uuid4().hex[:12]}"
        
        return cls(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            description=description,
            properties=kwargs.get("properties", {}),
            aliases=kwargs.get("aliases", []),
            embedding=kwargs.get("embedding"),
            source_id=kwargs.get("source_id"),
            source_url=kwargs.get("source_url"),
            confidence=kwargs.get("confidence", 1.0)
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "aliases": self.aliases,
            "has_embedding": self.embedding is not None,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=EntityType(data["entity_type"]),
            description=data.get("description", ""),
            properties=data.get("properties", {}),
            aliases=data.get("aliases", []),
            embedding=data.get("embedding"),
            source_id=data.get("source_id"),
            source_url=data.get("source_url"),
            confidence=data.get("confidence", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow()
        )
    
    def merge_with(self, other: "Entity") -> "Entity":
        """
        Merge this entity with another, keeping the most complete data.
        
        Args:
            other: Entity to merge with
            
        Returns:
            New merged entity
        """
        # Combine aliases
        all_aliases = list(set(self.aliases + other.aliases + [other.name]))
        if self.name in all_aliases:
            all_aliases.remove(self.name)
        
        # Merge properties
        merged_props = {**self.properties, **other.properties}
        
        # Use longer description
        description = self.description if len(self.description) >= len(other.description) else other.description
        
        # Average confidence
        avg_confidence = (self.confidence + other.confidence) / 2
        
        return Entity(
            id=self.id,  # Keep original ID
            name=self.name,
            entity_type=self.entity_type,
            description=description,
            properties=merged_props,
            aliases=all_aliases,
            embedding=self.embedding or other.embedding,
            source_id=self.source_id or other.source_id,
            source_url=self.source_url or other.source_url,
            confidence=avg_confidence,
            created_at=min(self.created_at, other.created_at),
            updated_at=datetime.utcnow()
        )
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
