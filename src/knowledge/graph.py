"""
Knowledge Graph Implementation.

Provides the main KnowledgeGraph class using NetworkX for in-memory operations
with optional persistence to Neo4j.
"""

import json
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.knowledge.entities import Entity, EntityType
from src.knowledge.relationships import Relationship, RelationshipType
from src.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class GraphStats:
    """Statistics about the knowledge graph."""
    entity_count: int
    relationship_count: int
    entity_types: dict[str, int]
    relationship_types: dict[str, int]
    communities: int = 0
    density: float = 0.0


@dataclass
class PathResult:
    """Result of a path search in the graph."""
    path: list[Entity]
    relationships: list[Relationship]
    total_weight: float
    hops: int


class KnowledgeGraph:
    """
    Knowledge Graph implementation using NetworkX.
    
    Features:
    - Entity and relationship storage
    - Path finding and traversal
    - Community detection
    - Semantic search (with embeddings)
    - Persistence to JSON/Neo4j
    
    Usage:
        graph = KnowledgeGraph()
        
        # Add entities
        person = Entity.create("John Doe", EntityType.PERSON, "A researcher")
        company = Entity.create("OpenAI", EntityType.COMPANY, "AI research lab")
        graph.add_entity(person)
        graph.add_entity(company)
        
        # Add relationship
        rel = Relationship.create(person.id, company.id, RelationshipType.WORKS_AT)
        graph.add_relationship(rel)
        
        # Query
        colleagues = graph.get_neighbors(person.id)
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize knowledge graph.
        
        Args:
            persist_path: Optional path for JSON persistence
        """
        try:
            import networkx as nx
            self._nx = nx
        except ImportError:
            raise ImportError("networkx required. Install with: pip install networkx")
        
        self.graph = self._nx.DiGraph()
        self.persist_path = Path(persist_path) if persist_path else None
        
        # Entity and relationship indexes
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        
        # Name to ID index for deduplication
        self._name_to_id: dict[str, str] = {}
        
        # Load persisted data if exists
        if self.persist_path and self.persist_path.exists():
            self._load()
    
    # ==================== Entity Operations ====================
    
    def add_entity(self, entity: Entity) -> str:
        """
        Add an entity to the graph.
        
        Args:
            entity: Entity to add
            
        Returns:
            Entity ID (may be existing if merged)
        """
        # Check for existing entity by name
        normalized_name = entity.name.lower().strip()
        if normalized_name in self._name_to_id:
            existing_id = self._name_to_id[normalized_name]
            existing = self._entities[existing_id]
            # Merge entities
            merged = existing.merge_with(entity)
            self._entities[existing_id] = merged
            self._update_node(merged)
            logger.debug(f"Merged entity: {entity.name}")
            return existing_id
        
        # Add new entity
        self._entities[entity.id] = entity
        self._name_to_id[normalized_name] = entity.id
        
        # Add to graph
        self.graph.add_node(
            entity.id,
            name=entity.name,
            type=entity.entity_type.value,
            description=entity.description,
            properties=entity.properties,
            embedding=entity.embedding
        )
        
        # Also index aliases
        for alias in entity.aliases:
            alias_norm = alias.lower().strip()
            if alias_norm not in self._name_to_id:
                self._name_to_id[alias_norm] = entity.id
        
        logger.debug(f"Added entity: {entity.name} ({entity.entity_type.value})")
        return entity.id
    
    def _update_node(self, entity: Entity):
        """Update node data in graph."""
        if entity.id in self.graph:
            self.graph.nodes[entity.id].update({
                "name": entity.name,
                "type": entity.entity_type.value,
                "description": entity.description,
                "properties": entity.properties,
                "embedding": entity.embedding
            })
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name (case-insensitive)."""
        normalized = name.lower().strip()
        entity_id = self._name_to_id.get(normalized)
        if entity_id:
            return self._entities.get(entity_id)
        return None
    
    def find_entities(
        self,
        entity_type: Optional[EntityType] = None,
        name_contains: Optional[str] = None,
        limit: int = 100
    ) -> list[Entity]:
        """
        Find entities matching criteria.
        
        Args:
            entity_type: Filter by type
            name_contains: Filter by name substring
            limit: Maximum results
            
        Returns:
            List of matching entities
        """
        results = []
        for entity in self._entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            if name_contains and name_contains.lower() not in entity.name.lower():
                continue
            results.append(entity)
            if len(results) >= limit:
                break
        return results
    
    def remove_entity(self, entity_id: str) -> bool:
        """Remove entity and its relationships."""
        if entity_id not in self._entities:
            return False
        
        entity = self._entities[entity_id]
        
        # Remove from name index
        normalized_name = entity.name.lower().strip()
        if normalized_name in self._name_to_id:
            del self._name_to_id[normalized_name]
        
        # Remove aliases from index
        for alias in entity.aliases:
            alias_norm = alias.lower().strip()
            if self._name_to_id.get(alias_norm) == entity_id:
                del self._name_to_id[alias_norm]
        
        # Remove relationships
        rels_to_remove = [
            rel_id for rel_id, rel in self._relationships.items()
            if rel.source_id == entity_id or rel.target_id == entity_id
        ]
        for rel_id in rels_to_remove:
            del self._relationships[rel_id]
        
        # Remove from graph
        if entity_id in self.graph:
            self.graph.remove_node(entity_id)
        
        # Remove entity
        del self._entities[entity_id]
        
        logger.debug(f"Removed entity: {entity.name}")
        return True
    
    # ==================== Relationship Operations ====================
    
    def add_relationship(self, relationship: Relationship) -> str:
        """
        Add a relationship to the graph.
        
        Args:
            relationship: Relationship to add
            
        Returns:
            Relationship ID
        """
        # Validate entities exist
        if relationship.source_id not in self._entities:
            raise ValueError(f"Source entity not found: {relationship.source_id}")
        if relationship.target_id not in self._entities:
            raise ValueError(f"Target entity not found: {relationship.target_id}")
        
        self._relationships[relationship.id] = relationship
        
        # Add edge to graph
        self.graph.add_edge(
            relationship.source_id,
            relationship.target_id,
            id=relationship.id,
            type=relationship.relationship_type.value,
            weight=relationship.weight,
            properties=relationship.properties
        )
        
        # Add reverse edge if bidirectional
        if relationship.bidirectional:
            reverse = relationship.reverse()
            self.graph.add_edge(
                reverse.source_id,
                reverse.target_id,
                id=reverse.id,
                type=reverse.relationship_type.value,
                weight=reverse.weight,
                properties=reverse.properties
            )
        
        source = self._entities[relationship.source_id]
        target = self._entities[relationship.target_id]
        logger.debug(f"Added relationship: {source.name} --[{relationship.relationship_type.value}]--> {target.name}")
        
        return relationship.id
    
    def get_relationship(self, rel_id: str) -> Optional[Relationship]:
        """Get relationship by ID."""
        return self._relationships.get(rel_id)
    
    def get_relationships_between(
        self,
        source_id: str,
        target_id: str
    ) -> list[Relationship]:
        """Get all relationships between two entities."""
        return [
            rel for rel in self._relationships.values()
            if rel.source_id == source_id and rel.target_id == target_id
        ]
    
    def remove_relationship(self, rel_id: str) -> bool:
        """Remove a relationship."""
        if rel_id not in self._relationships:
            return False
        
        rel = self._relationships[rel_id]
        
        # Remove from graph
        if self.graph.has_edge(rel.source_id, rel.target_id):
            self.graph.remove_edge(rel.source_id, rel.target_id)
        
        del self._relationships[rel_id]
        return True
    
    # ==================== Graph Traversal ====================
    
    def get_neighbors(
        self,
        entity_id: str,
        relationship_type: Optional[RelationshipType] = None,
        direction: str = "both"  # "outgoing", "incoming", "both"
    ) -> list[Entity]:
        """
        Get neighboring entities.
        
        Args:
            entity_id: Starting entity
            relationship_type: Filter by relationship type
            direction: Edge direction
            
        Returns:
            List of neighboring entities
        """
        if entity_id not in self.graph:
            return []
        
        neighbor_ids = set()
        
        if direction in ("outgoing", "both"):
            for _, target in self.graph.out_edges(entity_id):
                if relationship_type:
                    edge_data = self.graph.get_edge_data(entity_id, target)
                    if edge_data.get("type") != relationship_type.value:
                        continue
                neighbor_ids.add(target)
        
        if direction in ("incoming", "both"):
            for source, _ in self.graph.in_edges(entity_id):
                if relationship_type:
                    edge_data = self.graph.get_edge_data(source, entity_id)
                    if edge_data.get("type") != relationship_type.value:
                        continue
                neighbor_ids.add(source)
        
        return [self._entities[nid] for nid in neighbor_ids if nid in self._entities]
    
    def get_path(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 5
    ) -> Optional[PathResult]:
        """
        Find shortest path between two entities.
        
        Args:
            source_id: Starting entity
            target_id: Target entity
            max_hops: Maximum path length
            
        Returns:
            PathResult if path exists, None otherwise
        """
        try:
            path_ids = self._nx.shortest_path(
                self.graph,
                source_id,
                target_id
            )
            
            if len(path_ids) - 1 > max_hops:
                return None
            
            # Build path result
            entities = [self._entities[eid] for eid in path_ids]
            relationships = []
            total_weight = 0.0
            
            for i in range(len(path_ids) - 1):
                rels = self.get_relationships_between(path_ids[i], path_ids[i + 1])
                if rels:
                    relationships.append(rels[0])
                    total_weight += rels[0].weight
            
            return PathResult(
                path=entities,
                relationships=relationships,
                total_weight=total_weight,
                hops=len(path_ids) - 1
            )
            
        except self._nx.NetworkXNoPath:
            return None
    
    def get_subgraph(
        self,
        center_id: str,
        max_hops: int = 2,
        max_nodes: int = 50
    ) -> tuple[list[Entity], list[Relationship]]:
        """
        Get subgraph around an entity.
        
        Args:
            center_id: Center entity
            max_hops: Maximum distance from center
            max_nodes: Maximum nodes to include
            
        Returns:
            Tuple of (entities, relationships)
        """
        if center_id not in self.graph:
            return [], []
        
        # BFS to find nodes within max_hops
        visited = {center_id}
        current_level = {center_id}
        
        for _ in range(max_hops):
            next_level = set()
            for node in current_level:
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited and len(visited) < max_nodes:
                        visited.add(neighbor)
                        next_level.add(neighbor)
                for predecessor in self.graph.predecessors(node):
                    if predecessor not in visited and len(visited) < max_nodes:
                        visited.add(predecessor)
                        next_level.add(predecessor)
            if not next_level:
                break
            current_level = next_level
        
        # Get entities and relationships
        entities = [self._entities[eid] for eid in visited if eid in self._entities]
        relationships = [
            rel for rel in self._relationships.values()
            if rel.source_id in visited and rel.target_id in visited
        ]
        
        return entities, relationships
    
    # ==================== Semantic Search ====================
    
    async def semantic_search(
        self,
        query_embedding: list[float],
        entity_types: Optional[list[EntityType]] = None,
        top_k: int = 10
    ) -> list[tuple[Entity, float]]:
        """
        Search entities by embedding similarity.
        
        Args:
            query_embedding: Query vector
            entity_types: Filter by entity types
            top_k: Number of results
            
        Returns:
            List of (entity, similarity_score) tuples
        """
        import numpy as np
        
        query_vec = np.asarray(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []
        
        results = []
        
        for entity in self._entities.values():
            if entity_types and entity.entity_type not in entity_types:
                continue
            if not entity.embedding:
                continue
            
            ent_vec = np.asarray(entity.embedding, dtype=np.float32)
            ent_norm = np.linalg.norm(ent_vec)
            if ent_norm == 0:
                continue
            similarity = float(np.dot(query_vec, ent_vec) / (query_norm * ent_norm))
            results.append((entity, similarity))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    # ==================== Community Detection ====================
    
    def detect_communities(self) -> dict[str, int]:
        """
        Detect communities using Louvain algorithm.
        
        Returns:
            Dict mapping entity_id to community_id
        """
        try:
            from networkx.algorithms import community
            
            # Convert to undirected for community detection
            undirected = self.graph.to_undirected()
            
            # Use Louvain if available, else greedy modularity
            try:
                communities = community.louvain_communities(undirected)
            except AttributeError:
                communities = community.greedy_modularity_communities(undirected)
            
            # Convert to dict
            partition = {}
            for i, comm in enumerate(communities):
                for node in comm:
                    partition[node] = i
            
            logger.info(f"Detected {len(communities)} communities")
            return partition
            
        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return {}
    
    def get_community_entities(self, community_id: int) -> list[Entity]:
        """Get all entities in a community."""
        partition = self.detect_communities()
        return [
            self._entities[eid]
            for eid, cid in partition.items()
            if cid == community_id and eid in self._entities
        ]
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> GraphStats:
        """Get graph statistics."""
        entity_types: dict[str, int] = {}
        for entity in self._entities.values():
            t = entity.entity_type.value
            entity_types[t] = entity_types.get(t, 0) + 1
        
        rel_types: dict[str, int] = {}
        for rel in self._relationships.values():
            t = rel.relationship_type.value
            rel_types[t] = rel_types.get(t, 0) + 1
        
        # Calculate density
        n = len(self._entities)
        density = 0.0
        if n > 1:
            density = len(self._relationships) / (n * (n - 1))
        
        # Detect communities
        communities = len(set(self.detect_communities().values())) if self._entities else 0
        
        return GraphStats(
            entity_count=len(self._entities),
            relationship_count=len(self._relationships),
            entity_types=entity_types,
            relationship_types=rel_types,
            communities=communities,
            density=density
        )
    
    # ==================== Persistence ====================
    
    def save(self, path: Optional[str] = None):
        """Save graph to JSON file."""
        save_path = Path(path) if path else self.persist_path
        if not save_path:
            raise ValueError("No persist path specified")
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "entities": [e.to_dict() for e in self._entities.values()],
            "relationships": [r.to_dict() for r in self._relationships.values()],
            "saved_at": datetime.utcnow().isoformat()
        }
        
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved graph to {save_path}: {len(self._entities)} entities, {len(self._relationships)} relationships")
    
    def _load(self):
        """Load graph from JSON file."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        with open(self.persist_path) as f:
            data = json.load(f)
        
        # Load entities first
        for entity_data in data.get("entities", []):
            entity = Entity.from_dict(entity_data)
            self._entities[entity.id] = entity
            self._name_to_id[entity.name.lower().strip()] = entity.id
            self.graph.add_node(
                entity.id,
                name=entity.name,
                type=entity.entity_type.value,
                description=entity.description,
                properties=entity.properties,
                embedding=entity.embedding
            )
        
        # Load relationships
        for rel_data in data.get("relationships", []):
            rel = Relationship.from_dict(rel_data)
            if rel.source_id in self._entities and rel.target_id in self._entities:
                self._relationships[rel.id] = rel
                self.graph.add_edge(
                    rel.source_id,
                    rel.target_id,
                    id=rel.id,
                    type=rel.relationship_type.value,
                    weight=rel.weight,
                    properties=rel.properties
                )
        
        logger.info(f"Loaded graph from {self.persist_path}: {len(self._entities)} entities, {len(self._relationships)} relationships")
    
    def clear(self):
        """Clear all data from the graph."""
        self.graph.clear()
        self._entities.clear()
        self._relationships.clear()
        self._name_to_id.clear()
        logger.info("Graph cleared")
    
    # ==================== Context Building ====================
    
    def build_context(
        self,
        entity_ids: list[str],
        include_neighbors: bool = True,
        max_context_entities: int = 20
    ) -> str:
        """
        Build a context string from entities for LLM prompts.
        
        Args:
            entity_ids: Starting entity IDs
            include_neighbors: Include connected entities
            max_context_entities: Maximum entities to include
            
        Returns:
            Formatted context string
        """
        entities_to_include = set()
        
        for eid in entity_ids:
            if eid in self._entities:
                entities_to_include.add(eid)
                
                if include_neighbors and len(entities_to_include) < max_context_entities:
                    for neighbor in self.get_neighbors(eid):
                        entities_to_include.add(neighbor.id)
                        if len(entities_to_include) >= max_context_entities:
                            break
        
        if not entities_to_include:
            return ""
        
        lines = ["### Knowledge Graph Context"]
        
        # Add entities
        lines.append("\n**Entities:**")
        for eid in list(entities_to_include)[:max_context_entities]:
            entity = self._entities.get(eid)
            if entity:
                lines.append(f"- {entity.name} ({entity.entity_type.value}): {entity.description[:100]}")
        
        # Add relationships between included entities
        lines.append("\n**Relationships:**")
        for rel in self._relationships.values():
            if rel.source_id in entities_to_include and rel.target_id in entities_to_include:
                source = self._entities.get(rel.source_id)
                target = self._entities.get(rel.target_id)
                if source and target:
                    lines.append(f"- {source.name} --[{rel.relationship_type.value}]--> {target.name}")
        
        return "\n".join(lines)
