"""Code splitter for markdown code blocks with logical linking"""
import logging
from typing import List

from ..schema import SemanticChunk
from .markdown_parser import MarkdownElement
from ...text_processing.tokenizer_utils import TokenCounter
from ...text_processing.sentence_splitter import SentenceSplitter
from ...config import RAGChunkingConfig

from .utils import link_chunks, create_chunk

logger = logging.getLogger(__name__)

class CodeSplitter:
    """Splitter for code blocks - preserves logical structure and handles linking"""
    
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
        return self.config.chunking.max_chunk_size
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        content = element.content
        language = element.language or "unknown"
        token_count = self.token_counter.count_tokens(content)
        parent_section = header_path.split(" > ")[-1] if " > " in header_path else header_path
        chunk_type = f"code_{language}"
        
        if token_count <= self.max_chunk_size:
            chunks = [create_chunk(content, token_count, header_path, parent_section, chunk_type)]
        else:
            chunks = self._split_by_lines(content, chunk_type, header_path, parent_section)
        
        return link_chunks(chunks)

    def _split_by_lines(self, code_content: str, chunk_type: str, header_path: str, parent_section: str) -> List[SemanticChunk]:
        lines = code_content.split('\n')
        chunks, current_lines, current_tokens = [], [], 0
        
        for line in lines:
            line_tokens = self.token_counter.count_tokens(line)
            if current_tokens + line_tokens > self.max_chunk_size and current_lines:
                chunks.append(create_chunk("\n".join(current_lines), current_tokens, header_path, parent_section, chunk_type))
                current_lines, current_tokens = [line], line_tokens
            else:
                current_lines.append(line)
                current_tokens += line_tokens
        
        if current_lines:
            chunks.append(create_chunk("\n".join(current_lines), current_tokens, header_path, parent_section, chunk_type))
        return chunks