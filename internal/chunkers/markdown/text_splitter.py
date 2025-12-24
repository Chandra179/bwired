"""Text splitter for markdown paragraphs"""
from typing import List
import logging

from ...schema import SemanticChunk
from .markdown_parser import MarkdownElement
from ...text_processing.tokenizer_utils import TokenCounter
from ...text_processing.sentence_splitter import SentenceSplitter
from ...config import RAGChunkingConfig

logger = logging.getLogger(__name__)


class TextSplitter:
    """Splitter for text/paragraphs - uses sentence boundaries"""
    
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
        Chunk text/paragraph using sentence boundaries
        
        Strategy:
        1. If text fits in max_chunk_size, keep as single chunk
        2. Otherwise, split by sentences while respecting max size
        """
        content = element.content
        token_count = self.token_counter.count_tokens(content)
        
        # Text fits in one chunk
        if token_count <= self.max_chunk_size:
            chunk = self._create_chunk(content, header_path)
            logger.debug(f"Text chunked as single unit: {token_count} tokens")
            return [chunk]
        
        # Split large text by sentences
        logger.debug(f"Splitting large text: {token_count} tokens")
        return self._split_by_sentences(content, header_path)
    
    def _split_by_sentences(
        self, 
        text_content: str, 
        header_path: str
    ) -> List[SemanticChunk]:
        """Split text by sentences while respecting max size"""
        sentences = self.sentence_splitter.split_sentences(text_content)
        
        if not sentences:
            return [self._create_chunk(text_content, header_path)]
        
        chunks = []
        current_sentences = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.token_counter.count_tokens(sentence)
            
            # Single sentence exceeds limit - force add anyway
            if sentence_tokens > self.max_chunk_size:
                # Flush current chunk if exists
                if current_sentences:
                    chunk_content = ' '.join(current_sentences)
                    chunks.append(self._create_chunk(chunk_content, header_path))
                    current_sentences = []
                    current_tokens = 0
                
                # Add oversized sentence as its own chunk
                chunks.append(self._create_chunk(sentence, header_path))
                continue
            
            # Check if adding this sentence would exceed limit
            if current_tokens + sentence_tokens > self.max_chunk_size and current_sentences:
                # Flush current chunk
                chunk_content = ' '.join(current_sentences)
                chunks.append(self._create_chunk(chunk_content, header_path))
                
                # Start new chunk
                current_sentences = [sentence]
                current_tokens = sentence_tokens
            else:
                current_sentences.append(sentence)
                current_tokens += sentence_tokens
        
        # Flush remaining sentences
        if current_sentences:
            chunk_content = ' '.join(current_sentences)
            chunks.append(self._create_chunk(chunk_content, header_path))
        
        # Set split sequences
        self._set_split_sequences(chunks)
        
        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def _create_chunk(self, content: str, header_path: str) -> SemanticChunk:
        """Helper to create a single chunk"""
        return SemanticChunk(
            content=content,
            token_count=self.token_counter.count_tokens(content),
            chunk_type="text",
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