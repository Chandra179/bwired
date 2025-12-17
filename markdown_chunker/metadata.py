"""
Enhanced metadata for RAG-optimized chunks
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import uuid


@dataclass
class ChunkMetadata:
    """Comprehensive metadata for RAG chunks"""
    
    # --- REQUIRED FIELDS (Must come first) ---
    
    # Identity
    chunk_id: str
    document_id: str
    document_title: str
    
    # Content characteristics
    token_count: int
    chunk_type: str
    
    # Hierarchy and structure
    section_path: str
    section_level: int
    chunk_index: int
    
    # NEW: Search & Display Content (Moved up here because they are required)
    search_content: str   # Context-rich text for Vector DB
    
    # --- OPTIONAL FIELDS (Must come last) ---
    
    # RAG-specific metadata
    entities: Optional[Dict[str, List[str]]] = None
    
    # Multi-representation
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
        
        # Fallback if search_content wasn't generated
        # (Assuming your SemanticChunk class has this field now)
        final_search_text = getattr(chunk, 'search_content', None) or chunk.content
        
        return cls(
            chunk_id=chunk_id,
            document_id=document_id,
            document_title=document_title,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            section_path=chunk.section_path,
            section_level=chunk.section_level,
            chunk_index=chunk.chunk_index,
            
            # These are now required, so we pass them here
            search_content=final_search_text,
            
            # Optional fields follow
            entities=chunk.entities,
            has_multi_representation=chunk.has_multi_representation,
            natural_language_description=chunk.natural_language_description,
            extra=chunk.extra_metadata
        )