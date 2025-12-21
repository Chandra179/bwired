"""List splitting strategy"""
from typing import List
import logging

from .base_splitter import BaseSplitter
from ..schema import SemanticChunk
from ..parser import MarkdownElement

logger = logging.getLogger(__name__)


class ListSplitter(BaseSplitter):
    """Split lists by items when they exceed size limit"""
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        """Chunk list - keep intact if fits within limit, otherwise split by items"""
        
        token_count = self.token_counter.count_tokens(element.content)
        
        # Keep intact if it fits
        if token_count <= self.max_chunk_size:
            return [self._create_single_chunk(element.content, "list", header_path)]
        
        return self._split_by_items(element, header_path)
    
    def _split_by_items(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split list by items"""
        
        lines = element.content.split('\n')
        chunks = []
        current_items = []
        current_tokens = 0
        
        for line in lines:
            if not line.strip():
                continue
            
            line_tokens = self.token_counter.count_tokens(line)
            
            if current_tokens + line_tokens <= self.max_chunk_size:
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
        
        self._set_split_sequences(chunks)
        return chunks