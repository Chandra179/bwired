"""Code splitter for markdown code blocks - moved to splitters/markdown/"""
from typing import List
import logging

from ...schema import SemanticChunk
from ...parsers.markdown_parser import MarkdownElement  # UPDATED import path
from ..base_splitter import BaseSplitter  # UPDATED import path

logger = logging.getLogger(__name__)


class CodeSplitter(BaseSplitter):
    """Splitter for code blocks - preserves logical structure"""
    
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
            chunk = self._create_single_chunk(content, f"code_{language}", header_path)
            logger.debug(f"Code block chunked as single unit: {token_count} tokens")
            return [chunk]
        
        # Split large code block
        logger.debug(f"Splitting large code block: {token_count} tokens")
        return self._split_code_by_lines(content, language, header_path)
    
    def _split_code_by_lines(
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
                chunks.append(self._create_single_chunk(
                    chunk_content, 
                    f"code_{language}", 
                    header_path
                ))
                
                # Start new chunk
                current_lines = [line]
                current_tokens = line_tokens
            else:
                current_lines.append(line)
                current_tokens += line_tokens
        
        # Flush remaining lines
        if current_lines:
            chunk_content = '\n'.join(current_lines)
            chunks.append(self._create_single_chunk(
                chunk_content, 
                f"code_{language}", 
                header_path
            ))
        
        # Set split sequences
        self._set_split_sequences(chunks)
        
        logger.debug(f"Split code into {len(chunks)} chunks")
        return chunks