"""Base abstract class for document chunkers"""
from abc import ABC, abstractmethod
from typing import List
import logging

from .schema import SemanticChunk
from ..config import RAGChunkingConfig

logger = logging.getLogger(__name__)


class BaseDocumentChunker(ABC):
    """
    Abstract base class for document-level chunking.
    
    Defines the interface that all format-specific chunkers must implement.
    Each chunker handles: parsing → structure analysis → orchestrating element chunking
    """
    
    def __init__(self, config: RAGChunkingConfig):
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
        
        Args:
            content: Raw document content (format-specific)
            document_id: Unique document identifier
            
        Returns:
            List of semantic chunks with metadata
        """
        pass
    
    @property
    def max_chunk_size(self) -> int:
        """Maximum size for a chunk before overlap"""
        return self.config.max_chunk_size