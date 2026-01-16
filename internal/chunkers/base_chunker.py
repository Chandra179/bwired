"""Base abstract class for document chunkers"""
from abc import ABC, abstractmethod
from typing import List
import logging

from .schema import SemanticChunk
from ..config import Config

logger = logging.getLogger(__name__)


class BaseDocumentChunker(ABC):
    """
    Abstract base class for document-level chunking.
    
    Defines the interface that all format-specific chunkers must implement.
    Each chunker handles: parsing → structure analysis → orchestrating element chunking.
    Subclasses must implement the chunk_document method.
    
    Supported formats:
    - Markdown: MarkdownDocumentChunker (internal/chunkers/markdown/)
    - Future: HTML, PDF, plain text
    
    Attributes:
        config: Configuration dataclass with chunking parameters
    
    Note:
        This class uses the Template Method pattern, where chunk_document
        is the abstract method that subclasses implement, but the overall
        chunking workflow is defined here.
    """
    
    def __init__(self, config: Config):
        self.config = config
        logger.info(f"{self.__class__.__name__} initialized")
    
    @abstractmethod
    def chunk_document(
        self, 
        content: str, 
        document_id: str
    ) -> List[SemanticChunk]:
        """
        Chunk document content into semantic chunks.
        
        This method must be implemented by subclasses to handle
        format-specific parsing and chunking logic. The returned
        chunks should be optimized for RAG retrieval, maintaining
        semantic coherence while staying within token limits.
        
        Args:
            content: Raw document content (format-specific, e.g., Markdown string)
            document_id: Unique document identifier for tracking
            
        Returns:
            List of SemanticChunk objects with metadata including:
            - id: Unique chunk identifier
            - content: The chunk text
            - token_count: Number of tokens in chunk
            - chunk_type: Type of chunk (text, table, code, etc.)
            - parent_section: Immediate parent section heading
            - section_path: Full ancestry path (section > subsection > ...)
            - next_chunk_id: ID of next sequential chunk (for context)
            - prev_chunk_id: ID of previous sequential chunk
            - split_sequence: Split sequence number for ordering
        """
        pass
    
    @property
    def max_chunk_size(self) -> int:
        """
        Maximum size for a chunk before overlap is applied.
        
        Returns:
            Maximum token count for a chunk (from config.chunking.max_chunk_size)
        """
        return self.config.chunking.max_chunk_size