from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ChunkMetadata:
    document_id: str
    token_count: int
    chunk_type: str
    section_path: str
    
    split_sequence: Optional[str] = None  # e.g., "2/5"
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)        
        return data
    
    @classmethod
    def from_chunk(
        cls,
        chunk,
        document_id: str,
    ) -> 'ChunkMetadata':
        return cls(
            document_id=document_id,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            section_path=chunk.section_path,
            split_sequence=chunk.split_sequence,
        )