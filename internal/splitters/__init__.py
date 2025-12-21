"""Splitter factory and facade for backward compatibility"""
from typing import List

from .base_splitter import BaseSplitter
from .table_splitter import TableSplitter
from .code_splitter import CodeSplitter
from .list_splitter import ListSplitter
from .text_splitter import TextSplitter

from ..schema import SemanticChunk
from ..parser import MarkdownElement
from ..text_processing.tokenizer_utils import TokenCounter
from ..text_processing.sentence_splitter import SentenceSplitter
from ..config import RAGChunkingConfig


class ChunkSplitters:
    """
    Facade class for backward compatibility.
    Delegates to individual splitter classes.
    """
    
    def __init__(
        self, 
        config: RAGChunkingConfig, 
        sentence_splitter: SentenceSplitter, 
        token_counter: TokenCounter
    ):
        self.config = config
        self.sentence_splitter = sentence_splitter
        self.token_counter = token_counter
        
        self.table_splitter = TableSplitter(config, sentence_splitter, token_counter)
        self.code_splitter = CodeSplitter(config, sentence_splitter, token_counter)
        self.list_splitter = ListSplitter(config, sentence_splitter, token_counter)
        self.text_splitter = TextSplitter(config, sentence_splitter, token_counter)
    
    @property
    def max_chunk_size(self) -> int:
        """Maximum size for a chunk before overlap"""
        return self.config.max_chunk_size
    
    def chunk_table(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk table - delegates to TableSplitter"""
        return self.table_splitter.chunk(element, header_path)
    
    def chunk_code(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk code block - delegates to CodeSplitter"""
        return self.code_splitter.chunk(element, header_path)
    
    def chunk_list(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk list - delegates to ListSplitter"""
        return self.list_splitter.chunk(element, header_path)
    
    def chunk_text(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk text/paragraph - delegates to TextSplitter"""
        return self.text_splitter.chunk(element, header_path)


# Export for backward compatibility
__all__ = [
    'ChunkSplitters',
    'BaseSplitter',
    'TableSplitter',
    'CodeSplitter',
    'ListSplitter',
    'TextSplitter',
]