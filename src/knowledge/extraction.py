"""
Entity Extraction from Text.

Uses LLM to extract entities and relationships from research text.
"""

import json
import re
from typing import Any, Optional
from dataclasses import dataclass

from src.knowledge.entities import Entity, EntityType
from src.knowledge.relationships import Relationship, RelationshipType
from src.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    entities: list[Entity]
    relationships: list[Relationship]
    text_length: int
    extraction_model: str


# Entity extraction prompt
ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting structured knowledge from text.

Given the following text, extract all significant entities and their relationships.

TEXT:
{text}

Extract entities of these types:
- PERSON: Individual people (researchers, authors, etc.)
- ORGANIZATION: Companies, universities, research labs
- TECHNOLOGY: Software, hardware, frameworks, tools
- CONCEPT: Abstract ideas, theories, principles
- METHOD: Algorithms, techniques, approaches
- RESEARCH_PAPER: Published papers, articles
- DATASET: Data collections, benchmarks
- METRIC: Performance measures, evaluation criteria
- EVENT: Conferences, launches, discoveries
- LOCATION: Places, geographic entities
- PRODUCT: Commercial products, services

For each entity provide:
1. name: The entity's canonical name
2. type: One of the types above
3. description: A brief description (1-2 sentences)
4. aliases: Alternative names or abbreviations

For relationships, identify connections between entities:
- AUTHORED: Person authored a paper
- WORKS_AT: Person works at organization
- DEVELOPED_BY: Technology developed by organization/person
- USES: Technology/Method uses another
- BASED_ON: Built upon another concept/method
- COMPARED_TO: Evaluated against
- ACHIEVES: Method/Technology achieves metric
- PART_OF: Component of a larger system
- RELATED_TO: General association

Output ONLY valid JSON in this exact format:
{{
  "entities": [
    {{
      "name": "Entity Name",
      "type": "PERSON|ORGANIZATION|TECHNOLOGY|...",
      "description": "Brief description",
      "aliases": ["alias1", "alias2"]
    }}
  ],
  "relationships": [
    {{
      "source": "Source Entity Name",
      "target": "Target Entity Name", 
      "type": "AUTHORED|WORKS_AT|...",
      "evidence": "Quote or summary supporting this relationship"
    }}
  ]
}}

Be thorough but avoid extracting overly generic terms. Focus on domain-specific knowledge."""


class EntityExtractor:
    """
    Extracts entities and relationships from text using LLM.
    
    Features:
    - LLM-based extraction
    - Entity deduplication
    - Relationship validation
    - Batch processing
    
    Usage:
        extractor = EntityExtractor(llm_service)
        result = await extractor.extract(text)
        for entity in result.entities:
            print(entity.name, entity.entity_type)
    """
    
    def __init__(
        self,
        llm_service: Any,
        model: str = "gpt-oss:20b-cloud",
        embedding_service: Optional[Any] = None
    ):
        """
        Initialize extractor.
        
        Args:
            llm_service: LLM service for extraction
            model: Model to use
            embedding_service: Optional embedding service for entity embeddings
        """
        self.llm = llm_service
        self.model = model
        self.embedding_service = embedding_service
        
        # Type mappings
        self._entity_type_map = {t.value.upper(): t for t in EntityType}
        self._rel_type_map = {t.value.upper(): t for t in RelationshipType}
    
    async def extract(
        self,
        text: str,
        context: Optional[str] = None,
        generate_embeddings: bool = True
    ) -> ExtractionResult:
        """
        Extract entities and relationships from text.
        
        Args:
            text: Text to extract from
            context: Optional additional context
            generate_embeddings: Whether to generate entity embeddings
            
        Returns:
            ExtractionResult with entities and relationships
        """
        if not text.strip():
            return ExtractionResult(
                entities=[],
                relationships=[],
                text_length=0,
                extraction_model=self.model
            )
        
        # Truncate very long text
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.debug(f"Truncated text to {max_chars} chars for extraction")
        
        # Build prompt
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        
        try:
            # Call LLM with proper config
            from src.services.llm.models import LLMConfig
            config = LLMConfig(
                model=self.model,
                temperature=0.1,  # Low temp for consistent extraction
                max_tokens=4000,
                format="json"
            )
            result = await self.llm.generate(prompt=prompt, config=config)
            response = result.content
            
            # Parse response
            entities, relationships = self._parse_response(response)
            
            # Generate embeddings if requested
            if generate_embeddings and self.embedding_service and entities:
                entities = await self._add_embeddings(entities)
            
            logger.info(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
            
            return ExtractionResult(
                entities=entities,
                relationships=relationships,
                text_length=len(text),
                extraction_model=self.model
            )
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return ExtractionResult(
                entities=[],
                relationships=[],
                text_length=len(text),
                extraction_model=self.model
            )
    
    def _parse_response(
        self,
        response: str
    ) -> tuple[list[Entity], list[Relationship]]:
        """Parse LLM response into entities and relationships."""
        # Extract JSON from response
        json_str = self._extract_json(response)
        if not json_str:
            logger.warning("No valid JSON found in extraction response")
            return [], []
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction JSON: {e}")
            return [], []
        
        entities: list[Entity] = []
        entity_name_to_id: dict[str, str] = {}
        
        # Parse entities
        for entity_data in data.get("entities", []):
            try:
                name = entity_data.get("name", "").strip()
                type_str = entity_data.get("type", "").upper()
                description = entity_data.get("description", "")
                aliases = entity_data.get("aliases", [])
                
                if not name:
                    continue
                
                # Map type
                entity_type = self._entity_type_map.get(type_str, EntityType.CONCEPT)
                
                # Create entity
                entity = Entity.create(
                    name=name,
                    entity_type=entity_type,
                    description=description,
                    aliases=aliases if isinstance(aliases, list) else []
                )
                
                entities.append(entity)
                entity_name_to_id[name.lower()] = entity.id
                
            except Exception as e:
                logger.debug(f"Failed to parse entity: {e}")
                continue
        
        relationships: list[Relationship] = []
        
        # Parse relationships
        for rel_data in data.get("relationships", []):
            try:
                source_name = rel_data.get("source", "").strip().lower()
                target_name = rel_data.get("target", "").strip().lower()
                type_str = rel_data.get("type", "").upper()
                evidence = rel_data.get("evidence", "")
                
                # Find entity IDs
                source_id = entity_name_to_id.get(source_name)
                target_id = entity_name_to_id.get(target_name)
                
                if not source_id or not target_id:
                    # Try partial match
                    for name, eid in entity_name_to_id.items():
                        if source_name in name or name in source_name:
                            source_id = source_id or eid
                        if target_name in name or name in target_name:
                            target_id = target_id or eid
                
                if not source_id or not target_id:
                    continue
                
                # Map type
                rel_type = self._rel_type_map.get(type_str, RelationshipType.RELATED_TO)
                
                # Create relationship
                relationship = Relationship.create(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=rel_type,
                    evidence=[evidence] if evidence else [],
                    weight=0.8  # Default weight for extracted relationships
                )
                
                relationships.append(relationship)
                
            except Exception as e:
                logger.debug(f"Failed to parse relationship: {e}")
                continue
        
        return entities, relationships
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text."""
        # Try to find JSON block
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{[\s\S]*\}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_str = match.group(1) if '```' in pattern else match.group(0)
                # Validate it's valid JSON
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    continue
        
        return None
    
    async def _add_embeddings(self, entities: list[Entity]) -> list[Entity]:
        """Add embeddings to entities."""
        try:
            # Create texts for embedding
            texts = [
                f"{e.name}: {e.description}" if e.description else e.name
                for e in entities
            ]
            
            # Generate embeddings
            embeddings = await self.embedding_service.embed_batch(texts)
            
            # Add to entities
            for entity, embedding in zip(entities, embeddings):
                entity.embedding = embedding
            
            logger.debug(f"Added embeddings to {len(entities)} entities")
            
        except Exception as e:
            logger.warning(f"Failed to add embeddings: {e}")
        
        return entities
    
    async def extract_batch(
        self,
        texts: list[str],
        context: Optional[str] = None,
        generate_embeddings: bool = True
    ) -> list[ExtractionResult]:
        """
        Extract from multiple texts.
        
        Args:
            texts: List of texts
            context: Shared context
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            List of ExtractionResults
        """
        import asyncio
        
        results = []
        
        # Process in batches to avoid overwhelming LLM
        batch_size = 3
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = await asyncio.gather(*[
                self.extract(text, context, generate_embeddings)
                for text in batch
            ])
            results.extend(batch_results)
        
        return results
    
    def merge_results(self, results: list[ExtractionResult]) -> ExtractionResult:
        """
        Merge multiple extraction results.
        
        Args:
            results: List of ExtractionResults
            
        Returns:
            Merged ExtractionResult with deduplicated entities
        """
        all_entities: dict[str, Entity] = {}
        all_relationships: list[Relationship] = []
        total_length = 0
        
        # Merge entities (deduplicate by name)
        for result in results:
            total_length += result.text_length
            
            for entity in result.entities:
                key = entity.name.lower()
                if key in all_entities:
                    # Merge with existing
                    all_entities[key] = all_entities[key].merge_with(entity)
                else:
                    all_entities[key] = entity
            
            # Collect relationships (will need ID remapping)
            all_relationships.extend(result.relationships)
        
        return ExtractionResult(
            entities=list(all_entities.values()),
            relationships=all_relationships,
            text_length=total_length,
            extraction_model=results[0].extraction_model if results else self.model
        )
