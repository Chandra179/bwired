"""Table splitting strategy"""
from typing import List
import logging

from .base_splitter import BaseSplitter
from ..schema import SemanticChunk
from ..parser import MarkdownElement

logger = logging.getLogger(__name__)


class TableSplitter(BaseSplitter):
    """Split tables by rows when they exceed size limit"""
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk table - keep intact if fits within limit, otherwise split by rows"""
        
        token_count = self.token_counter.count_tokens(element.content)
        
        # Keep intact if it fits
        if token_count <= self.max_chunk_size:
            return [self._create_single_chunk(element.content, "table", header_path)]
        
        return self._split_by_rows(element, header_path)
    
    def _split_by_rows(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split large table by rows"""
        
        lines = element.content.split('\n')
        
        header_row = lines[0]
        separator = lines[1]
        data_rows = lines[2:]
        
        header_tokens = self.token_counter.count_tokens(header_row + '\n' + separator)
        available = self.max_chunk_size - header_tokens
        
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
                        split_sequence=None
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
                split_sequence=None
            ))
        
        self._set_split_sequences(chunks)
        return chunks