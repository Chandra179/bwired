"""Overlap handler for markdown chunks"""
import uuid
from typing import List, Optional
import logging

from ..schema import SemanticChunk
from ...processing.sentence_splitter import SentenceSplitter
from ...token_counter import TokenCounter

logger = logging.getLogger(__name__)


class OverlapHandler:
    """Manages overlap between adjacent chunks using sentence boundaries"""
    
    def __init__(self, sentence_splitter: SentenceSplitter):
        self.sentence_splitter = sentence_splitter
    
    def apply_overlap(
        self, 
        chunks: List[SemanticChunk],
        overlap_tokens: int,
        token_counter: TokenCounter,
        max_tokens: int
    ) -> List[SemanticChunk]:
        """
        Apply sliding window overlap to chunks within same section
        
        Args:
            chunks: List of chunks to process
            overlap_tokens: Number of tokens to overlap
            token_counter: TokenCounter instance
            max_tokens: Maximum tokens allowed per chunk
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
            
            if chunk.chunk_type == "table":
                result.append(chunk)
                continue
            
            prev_chunk = chunks[i - 1]
            
            # Only apply overlap if chunks are in same section
            if not self._same_section(chunk, prev_chunk):
                result.append(chunk)
                continue
            
            available_space = max_tokens - chunk.token_count - 10  # 10 buffer for safety
            safe_overlap = min(overlap_tokens, available_space)
            
            if safe_overlap <= 0:
                logger.debug(f"Skipping overlap for chunk {i}: no space available")
                result.append(chunk)
                continue
            
            overlap_text = self._extract_overlap_suffix(
                prev_chunk.content,
                safe_overlap,
                token_counter
            )
            
            if overlap_text:
                overlapped_content = f"{overlap_text}\n\n{chunk.content}"
                chunk_token_count = TokenCounter.count_tokens(chunk.content, token_counter.model_name, token_counter.tokenizer)
                overlap_token_count = TokenCounter.count_tokens(overlap_text, token_counter.model_name, token_counter.tokenizer)
                final_token_count = TokenCounter.count_tokens(overlapped_content, token_counter.model_name, token_counter.tokenizer)
                if final_token_count > max_tokens:
                    logger.warning(
                        f"Overlap caused chunk to exceed limit: {final_token_count} > {max_tokens}. \n"
                        f"Chunk token size: {chunk_token_count} \n"
                        f"Chunk length: {len(chunk.content)} \n"
                        f"Overlap token size: {overlap_token_count} \n"
                        f"Skipping overlap for this chunk."
                    )
                    result.append(chunk)
                    continue
                
                overlapped_chunk = SemanticChunk(
                    id=str(uuid.uuid4()),
                    content=overlapped_content,
                    token_count=TokenCounter.count_tokens(overlapped_content, token_counter.model_name, token_counter.tokenizer),
                    chunk_type=chunk.chunk_type,
                    prev_chunk_id=chunk.prev_chunk_id,
                    next_chunk_id=chunk.next_chunk_id,
                    parent_section=chunk.parent_section,
                    section_path=chunk.section_path,
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
        
        sentences = self.sentence_splitter.split_sentences(text)
        
        if not sentences:
            return None
        
        # Work backwards from end to accumulate target tokens
        overlap_sentences = []
        accumulated_tokens = 0
        
        for sentence in reversed(sentences):
            sentence_tokens = TokenCounter.count_tokens(sentence, token_counter.model_name, token_counter.tokenizer)
            
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