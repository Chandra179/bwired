"""Factory for creating format-specific document chunkers"""
from typing import Literal
import logging

from .base_chunker import BaseDocumentChunker
from .markdown import MarkdownDocumentChunker
from ..config import RAGChunkingConfig

logger = logging.getLogger(__name__)

# Type alias for supported formats
ChunkerFormat = Literal['markdown']


class ChunkerFactory:
    """Factory for creating document chunkers based on format"""
    
    @staticmethod
    def create(
        format: ChunkerFormat,
        config: RAGChunkingConfig
    ) -> BaseDocumentChunker:
        """
        Create a document chunker for the specified format
        
        Args:
            format: Document format ('markdown' currently supported)
            config: RAG chunking configuration
            
        Returns:
            Format-specific document chunker instance
            
        Raises:
            ValueError: If format is not supported
        """
        if format == 'markdown':
            logger.info("Creating MarkdownDocumentChunker")
            return MarkdownDocumentChunker(config)
        
        # Future formats can be added here:
        # elif format == 'html':
        #     from .html import HTMLDocumentChunker
        #     return HTMLDocumentChunker(config)
        
        raise ValueError(
            f"Unsupported document format: {format}. "
            f"Supported formats: markdown"
        )
    
    @staticmethod
    def supported_formats() -> list[str]:
        """Return list of supported document formats"""
        return ['markdown']