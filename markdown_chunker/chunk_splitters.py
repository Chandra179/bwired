"""
Element-specific chunking strategies for different markdown types
"""
from typing import List
import logging
from .schema import SemanticChunk

from .parser import MarkdownElement

logger = logging.getLogger(__name__)


class ChunkSplitters:
    """Collection of splitting strategies for different element types"""
    
    def __init__(self, config, sentence_splitter, token_counter):
        self.config = config
        self.sentence_splitter = sentence_splitter
        self.token_counter = token_counter
    
    def chunk_table(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Chunk table - keep intact if possible"""
        
        token_count = self.token_counter.count_tokens(element.content)
        
        # If table fits within target, keep it whole
        if token_count <= self.config.chunking.target_chunk_size or \
           self.config.chunking.keep_tables_intact:
            
            # If exceeds target, truncate
            if token_count > self.config.chunking.target_chunk_size:
                content = self.token_counter.truncate_to_tokens(
                    element.content,
                    self.config.chunking.target_chunk_size
                )
                token_count = self.config.chunking.target_chunk_size
            else:
                content = element.content
            
            return [SemanticChunk(
                content=content,
                token_count=token_count,
                chunk_type="table",
                section_path=header_path,
                is_continuation=False,
                split_sequence=None
            )]
        
        # Table is too large and splitting allowed
        return self._split_table_by_rows(element, header_path)
    
    def _split_table_by_rows(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split large table by rows"""
        from .semantic_chunker import SemanticChunk
        
        lines = element.content.split('\n')
        
        if len(lines) < 3:
            # Too small to split
            return self.chunk_table(element, header_path)
        
        header_row = lines[0]
        separator = lines[1]
        data_rows = lines[2:]
        
        header_tokens = self.token_counter.count_tokens(header_row + '\n' + separator)
        available = self.config.chunking.target_chunk_size - header_tokens - 20
        
        chunks = []
        current_rows = []
        current_tokens = 0
        
        for row in data_rows:
            row_tokens = self.token_counter.count_tokens(row)
            
            if current_tokens + row_tokens <= available:
                current_rows.append(row)
                current_tokens += row_tokens
            else:
                if current_rows:
                    table_chunk = '\n'.join([header_row, separator] + current_rows)
                    chunks.append(SemanticChunk(
                        content=table_chunk,
                        token_count=self.token_counter.count_tokens(table_chunk),
                        chunk_type="table",
                        section_path=header_path,
                        is_continuation=len(chunks) > 0,
                        split_sequence=None  # Will be set later
                    ))
                
                current_rows = [row]
                current_tokens = row_tokens
        
        # Add remaining
        if current_rows:
            table_chunk = '\n'.join([header_row, separator] + current_rows)
            chunks.append(SemanticChunk(
                content=table_chunk,
                token_count=self.token_counter.count_tokens(table_chunk),
                chunk_type="table",
                section_path=header_path,
                is_continuation=len(chunks) > 0,
                split_sequence=None  # Will be set later
            ))
        
        # Set split_sequence for all chunks
        total_parts = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            chunk.split_sequence = f"{i}/{total_parts}"
        
        return chunks
    
    def chunk_code(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Chunk code block - keep intact if possible"""
        from .semantic_chunker import SemanticChunk
        
        token_count = self.token_counter.count_tokens(element.content)
        
        # Try to keep code intact
        if token_count <= self.config.chunking.target_chunk_size or \
           self.config.chunking.keep_code_blocks_intact:
            
            # Truncate if necessary
            if token_count > self.config.chunking.target_chunk_size:
                content = self.token_counter.truncate_to_tokens(
                    element.content,
                    self.config.chunking.target_chunk_size
                )
                token_count = self.config.chunking.target_chunk_size
            else:
                content = element.content
            
            return [SemanticChunk(
                content=content,
                token_count=token_count,
                chunk_type="code_block",
                section_path=header_path,
                is_continuation=False,
                split_sequence=None
            )]
        
        # Code too large - split by lines
        return self._split_code_by_lines(element, header_path)
    
    def _split_code_by_lines(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split large code block by lines with contextual header"""
        from .semantic_chunker import SemanticChunk
        
        lines = element.content.split('\n')
        chunks = []
        
        # Identify Sticky Header (function/class definition)
        sticky_header = self._extract_code_header(lines)
        sticky_header_tokens = self.token_counter.count_tokens(sticky_header) if sticky_header else 0
        
        current_lines = []
        current_tokens = sticky_header_tokens
        
        # Start from beginning
        for line in lines:
            line_tokens = self.token_counter.count_tokens(line)
            
            if current_tokens + line_tokens <= self.config.chunking.target_chunk_size:
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
                        contextual_header=sticky_header if len(chunks) > 0 else None,
                        is_continuation=len(chunks) > 0,
                        split_sequence=None  # Will be set later
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
                contextual_header=sticky_header if len(chunks) > 0 else None,
                is_continuation=len(chunks) > 0,
                split_sequence=None
            ))
        
        # Set split_sequence
        total_parts = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            chunk.split_sequence = f"{i}/{total_parts}"
        
        return chunks
    
    def _extract_code_header(self, lines: List[str]) -> str:
        """Extract function/class definition as contextual header"""
        import re
        
        # Patterns for common function/class definitions
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
    
    def chunk_list(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Chunk list - keep items together"""
        from .semantic_chunker import SemanticChunk
        
        token_count = self.token_counter.count_tokens(element.content)
        
        # If list fits, keep whole
        if token_count <= self.config.chunking.target_chunk_size:
            return [SemanticChunk(
                content=element.content,
                token_count=token_count,
                chunk_type="list",
                section_path=header_path,
                is_continuation=False,
                split_sequence=None
            )]
        
        if self.config.chunking.keep_list_items_together:
            return self._split_list_by_items(element, header_path)
        else:
            # Treat as text
            return self.chunk_text(element, header_path)
    
    def _split_list_by_items(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split list by items"""
        from .semantic_chunker import SemanticChunk
        
        lines = element.content.split('\n')
        chunks = []
        current_items = []
        current_tokens = 0
        
        for line in lines:
            if not line.strip():
                continue
            
            line_tokens = self.token_counter.count_tokens(line)
            
            if current_tokens + line_tokens <= self.config.chunking.target_chunk_size:
                current_items.append(line)
                current_tokens += line_tokens
            else:
                if current_items:
                    list_chunk = '\n'.join(current_items)
                    chunks.append(SemanticChunk(
                        content=list_chunk,
                        token_count=self.token_counter.count_tokens(list_chunk),
                        chunk_type="list",
                        section_path=header_path,
                        is_continuation=len(chunks) > 0,
                        split_sequence=None
                    ))
                
                current_items = [line]
                current_tokens = line_tokens
        
        if current_items:
            list_chunk = '\n'.join(current_items)
            chunks.append(SemanticChunk(
                content=list_chunk,
                token_count=self.token_counter.count_tokens(list_chunk),
                chunk_type="list",
                section_path=header_path,
                is_continuation=len(chunks) > 0,
                split_sequence=None
            ))
        
        # Set split_sequence
        total_parts = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            chunk.split_sequence = f"{i}/{total_parts}"
        
        return chunks
    
    def chunk_text(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Chunk text/paragraph with sentence awareness"""
        from .semantic_chunker import SemanticChunk
        
        token_count = self.token_counter.count_tokens(element.content)
        
        # If fits in one chunk
        if token_count <= self.config.chunking.target_chunk_size:
            return [SemanticChunk(
                content=element.content,
                token_count=token_count,
                chunk_type=element.type.value,
                section_path=header_path,
                is_continuation=False,
                split_sequence=None
            )]
        
        # Split by sentences if configured
        if self.config.chunking.use_sentence_boundaries:
            text_chunks = self.sentence_splitter.split_into_chunks_by_sentences(
                element.content,
                self.config.chunking.target_chunk_size,
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
            total_parts = len(chunks)
            for i, chunk in enumerate(chunks, 1):
                chunk.split_sequence = f"{i}/{total_parts}"
        
        return chunks