from typing import Optional
from dataclasses import dataclass, field
from ..parser import MarkdownElement

@dataclass
class SemanticChunk:
    """Represents a semantically meaningful chunk for RAG"""
    id: str
    content: str
    token_count: int
    chunk_type: str
    
    # I. Recent Economic Developments
    parent_section: str
    
    # Enhanced ancestry - full hierarchical path of headings
    # I. Recent Economic Developments > Fiscal support helped shore up domestic demand
    section_path: str   
    
    split_sequence: Optional[str] = None
    next_chunk_id: Optional[str] = None
    prev_chunk_id: Optional[str] = None