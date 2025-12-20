"""Code block splitting strategy"""
from typing import List
import logging
import re

from .base_splitter import BaseSplitter
from ..schema import SemanticChunk
from ..parser import MarkdownElement

logger = logging.getLogger(__name__)


class CodeSplitter(BaseSplitter):
    """Split code blocks by lines when they exceed size limit"""
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk code block - keep intact if fits within limit, otherwise split by lines"""
        
        token_count = self.token_counter.count_tokens(element.content)
        
        # Keep intact if it fits
        if token_count <= self.max_chunk_size:
            return [self._create_single_chunk(element.content, "code_block", header_path)]
        
        # Too large - split by lines
        return self._split_by_lines(element, header_path)
    
    def _split_by_lines(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split large code block by lines with contextual header"""
        
        lines = element.content.split('\n')
        chunks = []
        
        # Identify sticky header (function/class definition)
        sticky_header = self._extract_code_header(lines)
        sticky_header_tokens = self.token_counter.count_tokens(sticky_header) if sticky_header else 0
        
        current_lines = []
        current_tokens = sticky_header_tokens
        
        for line in lines:
            line_tokens = self.token_counter.count_tokens(line)
            
            if current_tokens + line_tokens <= self.max_chunk_size:
                current_lines.append(line)
                current_tokens += line_tokens
            else:
                # Flush chunk
                if current_lines:
                    chunk_content = '\n'.join(current_lines)
                    
                    chunks.append(SemanticChunk(
                        content=chunk_content,
                        token_count=current_tokens,
                        chunk_type="code_block",
                        section_path=header_path,
                        is_continuation=len(chunks) > 0,
                        split_sequence=None
                    ))
                
                current_lines = [line]
                current_tokens = line_tokens + sticky_header_tokens
        
        # Add remaining
        if current_lines:
            chunk_content = '\n'.join(current_lines)
            chunks.append(SemanticChunk(
                content=chunk_content,
                token_count=current_tokens,
                chunk_type="code_block",
                section_path=header_path,
                is_continuation=len(chunks) > 0,
                split_sequence=None
            ))
        
        self._set_split_sequences(chunks)
        return chunks
    
    def _extract_code_header(self, lines: List[str]) -> str:
        """Extract function/class definition as contextual header"""
        patterns = [
            r'^(def\s+\w+\s*\([^)]*\)\s*:)',  # Python function
            r'^(class\s+\w+.*:)',  # Python class
            r'^(function\s+\w+\s*\([^)]*\))',  # JavaScript function
            r'^(const\s+\w+\s*=\s*\([^)]*\)\s*=>)',  # Arrow function
            r'^(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\([^)]*\)',  # Java/C#
        ]
        
        for line in lines[:10]:  # Check first 10 lines
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            for pattern in patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    return match.group(0)
        
        # Fallback: first non-empty line
        return next((line for line in lines if line.strip()), "")