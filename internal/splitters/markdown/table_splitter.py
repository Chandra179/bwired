"""Table splitter for markdown tables - moved to splitters/markdown/"""
from typing import List
import logging

from ...schema import SemanticChunk
from ...parsers.markdown_parser import MarkdownElement  # UPDATED import path
from ..base_splitter import BaseSplitter  # UPDATED import path

logger = logging.getLogger(__name__)


class TableSplitter(BaseSplitter):
    """Splitter for markdown tables - preserves structure"""
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """
        Chunk table while preserving structure
        
        Strategy:
        1. If table fits in max_chunk_size, keep as single chunk
        2. Otherwise, split by rows while preserving header
        """
        content = element.content
        token_count = self.token_counter.count_tokens(content)
        
        # Table fits in one chunk
        if token_count <= self.max_chunk_size:
            chunk = self._create_single_chunk(content, "table", header_path)
            logger.debug(f"Table chunked as single unit: {token_count} tokens")
            return [chunk]
        
        # Split large table by rows
        logger.debug(f"Splitting large table: {token_count} tokens")
        return self._split_table_by_rows(content, header_path)
    
    def _split_table_by_rows(
        self, 
        table_content: str, 
        header_path: str
    ) -> List[SemanticChunk]:
        """Split table by rows while keeping header in each chunk"""
        lines = table_content.split('\n')
        
        if len(lines) < 3:
            # Not enough for header + separator + data
            return [self._create_single_chunk(table_content, "table", header_path)]
        
        # Extract header and separator
        header_line = lines[0]
        separator_line = lines[1] if len(lines) > 1 else ""
        data_rows = lines[2:]
        
        header_block = f"{header_line}\n{separator_line}"
        header_tokens = self.token_counter.count_tokens(header_block)
        
        # Safety check
        if header_tokens > self.max_chunk_size * 0.8:
            logger.warning("Table header too large, returning as single chunk")
            return [self._create_single_chunk(table_content, "table", header_path)]
        
        chunks = []
        current_rows = []
        current_tokens = header_tokens
        
        for row in data_rows:
            row_tokens = self.token_counter.count_tokens(row)
            
            # Check if adding this row would exceed limit
            if current_tokens + row_tokens > self.max_chunk_size and current_rows:
                # Flush current chunk
                chunk_content = f"{header_block}\n" + "\n".join(current_rows)
                chunks.append(self._create_single_chunk(chunk_content, "table", header_path))
                
                # Start new chunk
                current_rows = [row]
                current_tokens = header_tokens + row_tokens
            else:
                current_rows.append(row)
                current_tokens += row_tokens
        
        # Flush remaining rows
        if current_rows:
            chunk_content = f"{header_block}\n" + "\n".join(current_rows)
            chunks.append(self._create_single_chunk(chunk_content, "table", header_path))
        
        # Set split sequences
        self._set_split_sequences(chunks)
        
        logger.debug(f"Split table into {len(chunks)} chunks")
        return chunks