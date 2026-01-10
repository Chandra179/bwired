"""Table splitter for markdown tables with external linking utility"""
import logging
from typing import List

from ..schema import SemanticChunk
from .markdown_parser import MarkdownElement
from ...token_counter import TokenCounter
from ...processing.sentence_splitter import SentenceSplitter
from ...config import Config

from .utils import link_chunks, create_chunk

logger = logging.getLogger(__name__)

class TableSplitter:
    """Splitter for markdown tables - preserves structure and uses linking"""
    
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
            chunks = [create_chunk(content, token_count, header_path, parent_section, "table")]
        else:
            chunks = self._split_by_rows(content, header_path, parent_section)
        
        return link_chunks(chunks)

    def _split_by_rows(self, table_content: str, header_path: str, parent_section: str) -> List[SemanticChunk]:
        lines = table_content.strip().split('\n')
        if len(lines) < 3:
            return [create_chunk(table_content, TokenCounter.count_tokens(table_content, self.token_counter.model_name, self.token_counter.tokenizer), header_path, parent_section, "table")]
        
        header_block = f"{lines[0]}\n{lines[1]}"
        header_tokens = TokenCounter.count_tokens(header_block, self.token_counter.model_name, self.token_counter.tokenizer)
        data_rows = lines[2:]
        
        chunks, current_rows, current_tokens = [], [], header_tokens
        
        for row in data_rows:
            row_tokens = TokenCounter.count_tokens(row, self.token_counter.model_name, self.token_counter.tokenizer)
            if current_tokens + row_tokens > self.max_chunk_size and current_rows:
                content = f"{header_block}\n" + "\n".join(current_rows)
                chunks.append(create_chunk(content, current_tokens, header_path, parent_section, "table"))
                current_rows, current_tokens = [row], header_tokens + row_tokens
            else:
                current_rows.append(row)
                current_tokens += row_tokens
        
        if current_rows:
            content = f"{header_block}\n" + "\n".join(current_rows)
            chunks.append(create_chunk(content, current_tokens, header_path, parent_section, "table"))
        return chunks