"""Base splitter class with common functionality"""
from typing import List
from abc import ABC, abstractmethod
import logging

from ..schema import SemanticChunk
from ..parsers.markdown_parser import MarkdownElement  # UPDATED import path
from ..text_processing.tokenizer_utils import TokenCounter
from ..text_processing.sentence_splitter import SentenceSplitter
from ..config import RAGChunkingConfig

logger = logging.getLogger(__name__)


class BaseSplitter(ABC):
    """Base class for all element splitters"""
    
    def __init__(
        self, 
        config: RAGChunkingConfig, 
        sentence_splitter: SentenceSplitter, 
        token_counter: TokenCounter
    ):
        self.config = config
        self.sentence_splitter = sentence_splitter
        self.token_counter = token_counter
    
    @property
    def max_chunk_size(self) -> int:
        """Maximum size for a chunk before overlap"""
        return self.config.max_chunk_size
    
    @abstractmethod
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """
        Chunk an element based on its type
        
        Args:
            element: Markdown element to chunk
            header_path: Hierarchical section path
            
        Returns:
            List of semantic chunks
        """
        pass
    
    def _create_single_chunk(
        self, 
        content: str, 
        chunk_type: str, 
        header_path: str
    ) -> SemanticChunk:
        """Helper to create a single chunk"""
        return SemanticChunk(
            content=content,
            token_count=self.token_counter.count_tokens(content),
            chunk_type=chunk_type,
            section_path=header_path,
            is_continuation=False,
            split_sequence=None
        )
    
    def _set_split_sequences(self, chunks: List[SemanticChunk]) -> None:
        """Set split_sequence metadata for all chunks"""
        if len(chunks) <= 1:
            return
        
        total_parts = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            chunk.split_sequence = f"{i}/{total_parts}"
            chunk.is_continuation = i > 1