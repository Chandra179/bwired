"""Text splitter for markdown paragraphs - moved to splitters/markdown/"""
from typing import List
import logging

from ...schema import SemanticChunk
from ...parsers.markdown_parser import MarkdownElement  # UPDATED import path
from ..base_splitter import BaseSplitter  # UPDATED import path

logger = logging.getLogger(__name__)


class TextSplitter(BaseSplitter):
    """Splitter for text/paragraphs - uses sentence boundaries"""
    
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
            chunk = self._create_single_chunk(content, "text", header_path)
            logger.debug(f"Text chunked as single unit: {token_count} tokens")
            return [chunk]
        
        # Split large text by sentences
        logger.debug(f"Splitting large text: {token_count} tokens")
        return self._split_text_by_sentences(content, header_path)
    
    def _split_text_by_sentences(
        self, 
        text_content: str, 
        header_path: str
    ) -> List[SemanticChunk]:
        """Split text by sentences while respecting max size"""
        sentences = self.sentence_splitter.split_sentences(text_content)
        
        if not sentences:
            return [self._create_single_chunk(text_content, "text", header_path)]
        
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
                    chunks.append(self._create_single_chunk(chunk_content, "text", header_path))
                    current_sentences = []
                    current_tokens = 0
                
                # Add oversized sentence as its own chunk
                chunks.append(self._create_single_chunk(sentence, "text", header_path))
                continue
            
            # Check if adding this sentence would exceed limit
            if current_tokens + sentence_tokens > self.max_chunk_size and current_sentences:
                # Flush current chunk
                chunk_content = ' '.join(current_sentences)
                chunks.append(self._create_single_chunk(chunk_content, "text", header_path))
                
                # Start new chunk
                current_sentences = [sentence]
                current_tokens = sentence_tokens
            else:
                current_sentences.append(sentence)
                current_tokens += sentence_tokens
        
        # Flush remaining sentences
        if current_sentences:
            chunk_content = ' '.join(current_sentences)
            chunks.append(self._create_single_chunk(chunk_content, "text", header_path))
        
        # Set split sequences
        self._set_split_sequences(chunks)
        
        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks