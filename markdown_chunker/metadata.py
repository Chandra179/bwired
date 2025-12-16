from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import uuid


@dataclass
class ChunkMetadata:
    """Metadata for a chunk stored in vector database"""
    
    # Identity
    chunk_id: str
    document_id: str
    document_title: str
    
    # Token information
    token_count: int
    chunk_type: str
    
    # Hierarchy and structure
    header_path: List[str]
    element_index: int
    chunk_index: int
    total_chunks: int
    
    # Line numbers
    line_start: int
    line_end: int
    
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
        
        # Convert header_path list to string for easier querying
        if 'header_path' in data and data['header_path']:
            data['header_path_str'] = ' > '.join(data['header_path'])
        
        return data
    
    @classmethod
    def from_chunk(cls, chunk, document_id: str, document_title: str) -> 'ChunkMetadata':
        """Create metadata from a Chunk object"""
        chunk_id = f"{document_id}_{chunk.element_index}_{chunk.chunk_index}_{uuid.uuid4().hex[:8]}"
        
        return cls(
            chunk_id=chunk_id,
            document_id=document_id,
            document_title=document_title,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            header_path=chunk.metadata.get('header_path', []),
            element_index=chunk.element_index,
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            line_start=chunk.metadata.get('line_start', 0),
            line_end=chunk.metadata.get('line_end', 0),
            extra={k: v for k, v in chunk.metadata.items() 
                   if k not in ['header_path', 'line_start', 'line_end']}
        )