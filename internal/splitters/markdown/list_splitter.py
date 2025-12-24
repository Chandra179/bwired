"""List splitter for markdown lists - moved to splitters/markdown/"""
from typing import List
import re
import logging

from ...schema import SemanticChunk
from ...parsers.markdown_parser import MarkdownElement  # UPDATED import path
from ..base_splitter import BaseSplitter  # UPDATED import path

logger = logging.getLogger(__name__)


class ListSplitter(BaseSplitter):
    """Splitter for markdown lists - preserves item boundaries"""
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """
        Chunk list while preserving item boundaries
        
        Strategy:
        1. If list fits in max_chunk_size, keep as single chunk
        2. Otherwise, split by items while respecting max size
        """
        content = element.content
        token_count = self.token_counter.count_tokens(content)
        
        # List fits in one chunk
        if token_count <= self.max_chunk_size:
            chunk = self._create_single_chunk(content, "list", header_path)
            logger.debug(f"List chunked as single unit: {token_count} tokens")
            return [chunk]
        
        # Split large list by items
        logger.debug(f"Splitting large list: {token_count} tokens")
        return self._split_list_by_items(content, header_path)
    
    def _split_list_by_items(
        self, 
        list_content: str, 
        header_path: str
    ) -> List[SemanticChunk]:
        """Split list by items while respecting max size"""
        items = self._extract_list_items(list_content)
        
        if not items:
            return [self._create_single_chunk(list_content, "list", header_path)]
        
        chunks = []
        current_items = []
        current_tokens = 0
        
        for item in items:
            item_tokens = self.token_counter.count_tokens(item)
            
            # Check if adding this item would exceed limit
            if current_tokens + item_tokens > self.max_chunk_size and current_items:
                # Flush current chunk
                chunk_content = '\n'.join(current_items)
                chunks.append(self._create_single_chunk(chunk_content, "list", header_path))
                
                # Start new chunk
                current_items = [item]
                current_tokens = item_tokens
            else:
                current_items.append(item)
                current_tokens += item_tokens
        
        # Flush remaining items
        if current_items:
            chunk_content = '\n'.join(current_items)
            chunks.append(self._create_single_chunk(chunk_content, "list", header_path))
        
        # Set split sequences
        self._set_split_sequences(chunks)
        
        logger.debug(f"Split list into {len(chunks)} chunks")
        return chunks
    
    def _extract_list_items(self, list_content: str) -> List[str]:
        """Extract individual list items, handling nested content"""
        items = []
        current_item = []
        lines = list_content.split('\n')
        
        for line in lines:
            # Check if this is a new list item
            if self._is_list_marker(line):
                # Save previous item if exists
                if current_item:
                    items.append('\n'.join(current_item))
                # Start new item
                current_item = [line]
            else:
                # Continuation of current item
                if current_item:
                    current_item.append(line)
        
        # Save last item
        if current_item:
            items.append('\n'.join(current_item))
        
        return items
    
    def _is_list_marker(self, line: str) -> bool:
        """Check if line starts a new list item"""
        stripped = line.lstrip()
        
        # Unordered list markers
        if stripped.startswith(('- ', '* ', '+ ')):
            return True
        
        # Ordered list markers
        if re.match(r'^\d+\.\s', stripped):
            return True
        
        return False