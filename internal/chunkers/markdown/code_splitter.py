"""Code splitter for markdown code blocks"""
from typing import List
import logging

from ..schema import SemanticChunk
from .markdown_parser import MarkdownElement
from ...text_processing.tokenizer_utils import TokenCounter
from ...text_processing.sentence_splitter import SentenceSplitter
from ...config import RAGChunkingConfig

logger = logging.getLogger(__name__)


class CodeSplitter:
    """Splitter for code blocks - preserves logical structure"""
    
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
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """
        Chunk code block while preserving structure
        
        Strategy:
        1. If code fits in max_chunk_size, keep as single chunk
        2. Otherwise, split by logical boundaries (functions, classes, blank lines)
        """
        content = element.content
        language = element.language or "unknown"
        token_count = self.token_counter.count_tokens(content)
        
        # Code fits in one chunk
        if token_count <= self.max_chunk_size:
            chunk = self._create_chunk(content, language, header_path)
            logger.debug(f"Code block chunked as single unit: {token_count} tokens")
            return [chunk]
        
        # Split large code block
        logger.debug(f"Splitting large code block: {token_count} tokens")
        return self._split_by_lines(content, language, header_path)
    
    def _split_by_lines(
        self, 
        code_content: str, 
        language: str,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split code by lines while respecting max size"""
        lines = code_content.split('\n')
        chunks = []
        current_lines = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = self.token_counter.count_tokens(line)
            
            # Check if adding this line would exceed limit
            if current_tokens + line_tokens > self.max_chunk_size and current_lines:
                # Flush current chunk
                chunk_content = '\n'.join(current_lines)
                chunks.append(self._create_chunk(chunk_content, language, header_path))
                
                # Start new chunk
                current_lines = [line]
                current_tokens = line_tokens
            else:
                current_lines.append(line)
                current_tokens += line_tokens
        
        # Flush remaining lines
        if current_lines:
            chunk_content = '\n'.join(current_lines)
            chunks.append(self._create_chunk(chunk_content, language, header_path))
        
        # Set split sequences
        self._set_split_sequences(chunks)
        
        logger.debug(f"Split code into {len(chunks)} chunks")
        return chunks
    
    def _create_chunk(self, content: str, language: str, header_path: str) -> SemanticChunk:
        """Helper to create a single chunk"""
        return SemanticChunk(
            content=content,
            token_count=self.token_counter.count_tokens(content),
            chunk_type=f"code_{language}",
            section_path=header_path,
            split_sequence=None
        )
    
    def _set_split_sequences(self, chunks: List[SemanticChunk]) -> None:
        """Set split_sequence metadata for all chunks"""
        if len(chunks) <= 1:
            return
        
        total_parts = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            chunk.split_sequence = f"{i}/{total_parts}"