"""
Enhanced metadata for RAG-optimized chunks
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import uuid


@dataclass
class ChunkMetadata:
    """Comprehensive metadata for RAG chunks"""
    
    # Identity
    chunk_id: str
    document_id: str
    document_title: str
    
    # Content characteristics
    token_count: int
    chunk_type: str  # paragraph, table, code, list, etc.
    
    # Hierarchy and structure
    section_path: str  # Full hierarchical header path (e.g., "Introduction > Getting Started > Installation")
    section_level: int  # Depth in hierarchy
    chunk_index: int  # Index within section
    
    # RAG-specific metadata
    entities: Optional[Dict[str, List[str]]] = None  # {entity_type: [entities]}
    
    # Multi-representation (for tables/code)
    has_multi_representation: bool = False
    natural_language_description: Optional[str] = None
    
    # Additional metadata
    extra: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        
        # Flatten extra metadata into main dict
        if self.extra:
            extra = data.pop('extra')
            data.update(extra)
        else:
            data.pop('extra', None)
        
        # Handle None values
        data = {k: v for k, v in data.items() if v is not None}
        
        return data
    
    @classmethod
    def from_chunk(
        cls,
        chunk,  # SemanticChunk instance
        document_id: str,
        document_title: str
    ) -> 'ChunkMetadata':
        """Create metadata from a SemanticChunk object"""
        chunk_id = f"{document_id}_{chunk.chunk_index}_{uuid.uuid4().hex[:8]}"
        
        return cls(
            chunk_id=chunk_id,
            document_id=document_id,
            document_title=document_title,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            section_path=chunk.section_path,
            section_level=chunk.section_level,
            chunk_index=chunk.chunk_index,
            entities=chunk.entities,
            has_multi_representation=chunk.has_multi_representation,
            natural_language_description=chunk.natural_language_description,
            extra=chunk.extra_metadata
        )