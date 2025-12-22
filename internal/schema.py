from typing import Optional
from dataclasses import dataclass, field
from .parser import MarkdownElement

@dataclass
class SemanticChunk:
    """Represents a semantically meaningful chunk for RAG"""
    content: str
    token_count: int
    chunk_type: str
    
    # Enhanced ancestry - full hierarchical path of headings
    section_path: str 
    
    # Relationship tracking
    is_continuation: bool = False 
    split_sequence: Optional[str] = None