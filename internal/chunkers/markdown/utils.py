import uuid
import logging
from typing import List
from ..schema import SemanticChunk

logger = logging.getLogger(__name__)

def link_chunks(chunks: List[SemanticChunk]) -> List[SemanticChunk]:
    """Assign bidirectional links and sequence metadata."""
    total_parts = len(chunks)
    if total_parts <= 1:
        return chunks

    for i, chunk in enumerate(chunks):
        chunk.split_sequence = f"{i+1}/{total_parts}"
        if i > 0:
            chunk.prev_chunk_id = chunks[i-1].id
        if i < total_parts - 1:
            chunk.next_chunk_id = chunks[i+1].id
            
    return chunks

def create_chunk(content: str, token_count: int, header_path: str, parent_section: str, chunk_type: str) -> SemanticChunk:
    """Standardized helper to instantiate a SemanticChunk with a unique ID."""
    return SemanticChunk(
        id=str(uuid.uuid4()),
        content=content,
        token_count=token_count,
        chunk_type=chunk_type,
        parent_section=parent_section,
        section_path=header_path
    )