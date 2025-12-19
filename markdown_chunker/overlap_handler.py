"""
Sliding window overlap handler for chunk continuity
"""
from typing import List, Optional
import logging
from .schema import SemanticChunk

from .sentence_splitter import SentenceSplitter
from .tokenizer_utils import TokenCounter

logger = logging.getLogger(__name__)


class OverlapHandler:
    """Manages overlap between adjacent chunks using sentence boundaries"""
    
    def __init__(self, sentence_splitter: SentenceSplitter):
        self.sentence_splitter = sentence_splitter
    
    def apply_overlap(
        self, 
        chunks: List[SemanticChunk],
        overlap_tokens: int,
        token_counter: TokenCounter
    ) -> List[SemanticChunk]:
        """
        Apply sliding window overlap to chunks within same section
        
        Args:
            chunks: List of chunks to process
            overlap_tokens: Number of tokens to overlap
            token_counter: TokenCounter instance
            
        Returns:
            Chunks with overlap applied
        """
        if overlap_tokens <= 0 or len(chunks) <= 1:
            return chunks
        
        result = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk - no prefix overlap needed
                result.append(chunk)
                continue
            
            prev_chunk = chunks[i - 1]
            
            # Only apply overlap if chunks are in same section
            if not self._same_section(chunk, prev_chunk):
                result.append(chunk)
                continue
            
            # Extract overlap text from previous chunk
            overlap_text = self._extract_overlap_suffix(
                prev_chunk.content,
                overlap_tokens,
                token_counter
            )
            
            if overlap_text:
                # Prepend overlap to current chunk
                overlapped_content = f"{overlap_text}\n\n{chunk.content}"
                
                # Create new chunk with overlap
                from .semantic_chunker import SemanticChunk
                overlapped_chunk = SemanticChunk(
                    content=overlapped_content,
                    token_count=token_counter.count_tokens(overlapped_content),
                    chunk_type=chunk.chunk_type,
                    section_path=chunk.section_path,
                    source_element=chunk.source_element,
                    contextual_header=chunk.contextual_header,
                    is_continuation=chunk.is_continuation,
                    split_sequence=chunk.split_sequence
                )
                result.append(overlapped_chunk)
            else:
                result.append(chunk)
        
        logger.debug(f"Applied overlap to {len(chunks)} chunks")
        return result
    
    def _same_section(self, chunk1, chunk2) -> bool:
        """Check if two chunks are in the same section"""
        return chunk1.section_path == chunk2.section_path
    
    def _extract_overlap_suffix(
        self,
        text: str,
        target_tokens: int,
        token_counter
    ) -> Optional[str]:
        """
        Extract the last N tokens from text at sentence boundaries
        
        Args:
            text: Source text
            target_tokens: Target number of tokens for overlap
            token_counter: TokenCounter instance
            
        Returns:
            Overlap text or None
        """
        if not text or target_tokens <= 0:
            return None
        
        # Split into sentences
        sentences = self.sentence_splitter.split_sentences(text)
        
        if not sentences:
            return None
        
        # Work backwards from end to accumulate target tokens
        overlap_sentences = []
        accumulated_tokens = 0
        
        for sentence in reversed(sentences):
            sentence_tokens = token_counter.count_tokens(sentence)
            
            # Stop if adding this sentence would exceed target significantly
            if accumulated_tokens > 0 and accumulated_tokens + sentence_tokens > target_tokens * 1.5:
                break
            
            overlap_sentences.insert(0, sentence)
            accumulated_tokens += sentence_tokens
            
            # Stop if we've reached target
            if accumulated_tokens >= target_tokens:
                break
        
        if not overlap_sentences:
            return None
        
        return ' '.join(overlap_sentences)