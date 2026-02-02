"""List splitter for markdown lists with external linking utility"""
import re
import logging
from typing import List

from ..schema import SemanticChunk
from .markdown_parser import MarkdownElement
from ...token_counter import TokenCounter
from ...processing.sentence_splitter import SentenceSplitter
from ...config import Config

from .utils import link_chunks, create_chunk

logger = logging.getLogger(__name__)

class ListSplitter:
    """Splitter for markdown lists - preserves item boundaries and handles linking"""
    
    def __init__(
        self, 
        config: Config, 
        sentence_splitter: SentenceSplitter, 
        token_counter: TokenCounter
    ):
        self.config = config
        self.sentence_splitter = sentence_splitter
        self.token_counter = token_counter
    
    @property
    def max_chunk_size(self) -> int:
        return self.config.chunking.max_chunk_size
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        content = element.content
        token_count = TokenCounter.count_tokens(content, self.token_counter.model_name, self.token_counter.tokenizer)
        parent_section = header_path.split(" > ")[-1] if " > " in header_path else header_path
        
        if token_count <= self.max_chunk_size:
            chunks = [create_chunk(content, token_count, header_path, parent_section, "list")]
        else:
            chunks = self._split_by_items(content, header_path, parent_section)
        
        return link_chunks(chunks)

    def _split_by_items(self, list_content: str, header_path: str, parent_section: str) -> List[SemanticChunk]:
        items = self._extract_list_items(list_content)
        if not items:
            return [create_chunk(list_content, TokenCounter.count_tokens(list_content, self.token_counter.model_name, self.token_counter.tokenizer), header_path, parent_section, "list")]
        
        chunks, current_items, current_tokens = [], [], 0
        for item in items:
            item_tokens = TokenCounter.count_tokens(item, self.token_counter.model_name, self.token_counter.tokenizer)
            if current_tokens + item_tokens > self.max_chunk_size and current_items:
                chunks.append(create_chunk("\n".join(current_items), current_tokens, header_path, parent_section, "list"))
                current_items, current_tokens = [item], item_tokens
            else:
                current_items.append(item)
                current_tokens += item_tokens
        
        if current_items:
            chunks.append(create_chunk("\n".join(current_items), current_tokens, header_path, parent_section, "list"))
        return chunks
    
    def _extract_list_items(self, list_content: str) -> List[str]:
        """Extract individual list items, handling nested content"""
        items = []
        current_item = []
        lines = list_content.split('\n')
        
        for line in lines:
            if self._is_list_marker(line):
                if current_item:
                    items.append('\n'.join(current_item))
                current_item = [line]
            else:
                if current_item:
                    current_item.append(line)
        
        if current_item:
            items.append('\n'.join(current_item))
        
        return items
    
    def _is_list_marker(self, line: str) -> bool:
        """Check if line starts a new list item"""
        stripped = line.lstrip()
        # Unordered or Ordered markers
        return stripped.startswith(('- ', '* ', '+ ')) or bool(re.match(r'^\d+\.\s', stripped))