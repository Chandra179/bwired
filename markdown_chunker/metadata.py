from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ChunkMetadata:
    """Comprehensive metadata for RAG chunks with relationship tracking"""
    
    document_id: str
    token_count: int
    chunk_type: str
    section_path: str  # Enhanced ancestry path
    
    # Relationship tracking
    is_continuation: bool = False
    split_sequence: Optional[str] = None  # e.g., "2/5"
    
    # Contextual information
    contextual_header: Optional[str] = None
    
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
        
        # Handle None values - remove them for cleaner storage
        data = {k: v for k, v in data.items() if v is not None}
        
        return data
    
    @classmethod
    def from_chunk(
        cls,
        chunk,
        document_id: str,
    ) -> 'ChunkMetadata':
        """Create metadata from a SemanticChunk object"""
        
        return cls(
            document_id=document_id,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            section_path=chunk.section_path,
            is_continuation=chunk.is_continuation,
            split_sequence=chunk.split_sequence,
            contextual_header=chunk.contextual_header,
        )