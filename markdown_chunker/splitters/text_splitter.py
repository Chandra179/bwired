"""Text/paragraph splitting strategy"""
from typing import List
import logging

from .base_splitter import BaseSplitter
from ..schema import SemanticChunk
from ..parser import MarkdownElement

logger = logging.getLogger(__name__)


class TextSplitter(BaseSplitter):
    """Split text/paragraphs with sentence awareness"""
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk text/paragraph with sentence awareness"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # Keep intact if it fits
        if token_count <= self.max_chunk_size:
            return [SemanticChunk(
                content=element.content,
                token_count=token_count,
                chunk_type=element.type.value,
                section_path=header_path,
                is_continuation=False,
                split_sequence=None
            )]
        
        # Too large - split by sentences if configured
        if self.config.chunking.use_sentence_boundaries:
            text_chunks = self.sentence_splitter.split_into_chunks_by_sentences(
                element.content,
                self.max_chunk_size,
                self.token_counter
            )
        else:
            # Fallback to simple word-based splitting
            text_chunks = [element.content]
        
        chunks = []
        for i, text_chunk in enumerate(text_chunks):
            chunks.append(SemanticChunk(
                content=text_chunk,
                token_count=self.token_counter.count_tokens(text_chunk),
                chunk_type=element.type.value,
                section_path=header_path,
                is_continuation=i > 0,
                split_sequence=None
            ))
        
        # Set split_sequence if split occurred
        if len(chunks) > 1:
            self._set_split_sequences(chunks)
        
        return chunks