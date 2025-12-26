from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ChunkMetadata:
    id: str
    document_id: str
    token_count: int
    chunk_type: str
    parent_section: str
    section_path: str
    next_chunk_id: Optional[str] = None
    prev_chunk_id: Optional[str] = None
    split_sequence: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)        
        return data
    
    @classmethod
    def from_chunk(
        cls,
        chunk,
        document_id: str,
    ) -> 'ChunkMetadata':
        """
        Creates ChunkMetadata from a SemanticChunk.
        Ensures all required positional arguments are passed in order.
        """
        return cls(
            document_id=document_id,
            id=chunk.id,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            parent_section=chunk.parent_section, 
            section_path=chunk.section_path,
            next_chunk_id=chunk.next_chunk_id,
            prev_chunk_id=chunk.prev_chunk_id,
            split_sequence=chunk.split_sequence,
        )