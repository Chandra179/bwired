"""List splitter for markdown lists"""
from typing import List
import re
import logging

from ...schema import SemanticChunk
from .markdown_parser import MarkdownElement
from ...text_processing.tokenizer_utils import TokenCounter
from ...text_processing.sentence_splitter import SentenceSplitter
from ...config import RAGChunkingConfig

logger = logging.getLogger(__name__)


class ListSplitter:
    """Splitter for markdown lists - preserves item boundaries"""
    
    def __init__(
        self, 
        config: RAGChunkingConfig, 
        sentence_splitter: SentenceSplitter, 
        token_counter: TokenCounter
    ):
        self.config = config
        self.sentence_splitter = sentence_splitter
        self.token_counter = token_counter
    
    @property
    def max_chunk_size(self) -> int:
        """Maximum size for a chunk before overlap"""
        return self.config.max_chunk_size
    
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
            chunk = self._create_chunk(content, header_path)
            logger.debug(f"List chunked as single unit: {token_count} tokens")
            return [chunk]
        
        # Split large list by items
        logger.debug(f"Splitting large list: {token_count} tokens")
        return self._split_by_items(content, header_path)
    
    def _split_by_items(
        self, 
        list_content: str, 
        header_path: str
    ) -> List[SemanticChunk]:
        """Split list by items while respecting max size"""
        items = self._extract_list_items(list_content)
        
        if not items:
            return [self._create_chunk(list_content, header_path)]
        
        chunks = []
        current_items = []
        current_tokens = 0
        
        for item in items:
            item_tokens = self.token_counter.count_tokens(item)
            
            # Check if adding this item would exceed limit
            if current_tokens + item_tokens > self.max_chunk_size and current_items:
                # Flush current chunk
                chunk_content = '\n'.join(current_items)
                chunks.append(self._create_chunk(chunk_content, header_path))
                
                # Start new chunk
                current_items = [item]
                current_tokens = item_tokens
            else:
                current_items.append(item)
                current_tokens += item_tokens
        
        # Flush remaining items
        if current_items:
            chunk_content = '\n'.join(current_items)
            chunks.append(self._create_chunk(chunk_content, header_path))
        
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
    
    def _create_chunk(self, content: str, header_path: str) -> SemanticChunk:
        """Helper to create a single chunk"""
        return SemanticChunk(
            content=content,
            token_count=self.token_counter.count_tokens(content),
            chunk_type="list",
            section_path=header_path,
            is_continuation=False,
            split_sequence=None
        )
    
    def _set_split_sequences(self, chunks: List[SemanticChunk]) -> None:
        """Set split_sequence metadata for all chunks"""
        if len(chunks) <= 1:
            return
        
        total_parts = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            chunk.split_sequence = f"{i}/{total_parts}"
            chunk.is_continuation = i > 1