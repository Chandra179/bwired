"""Text splitter for markdown paragraphs with external linking utility"""
import logging
from typing import List

from ..schema import SemanticChunk
from .markdown_parser import MarkdownElement
from ...text_processing.tokenizer_utils import TokenCounter
from ...text_processing.sentence_splitter import SentenceSplitter
from ...config import RAGChunkingConfig

from .utils import link_chunks, create_chunk

logger = logging.getLogger(__name__)

class TextSplitter:
    """Splitter for text/paragraphs - uses sentence boundaries"""
    
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
        # Accessing nested config based on your previous RAGChunkingConfig update
        return self.config.chunking.max_chunk_size
    
    def chunk(self, element: MarkdownElement, header_path: str) -> List[SemanticChunk]:
        content = element.content
        token_count = self.token_counter.count_tokens(content)
        parent_section = header_path.split(" > ")[-1] if " > " in header_path else header_path
        
        if token_count <= self.max_chunk_size:
            chunks = [create_chunk(content, token_count, header_path, parent_section, "text")]
        else:
            chunks = self._split_by_sentences(content, header_path, parent_section)
        
        return link_chunks(chunks)
    
    def _split_by_sentences(self, text_content: str, header_path: str, parent_section: str) -> List[SemanticChunk]:
        sentences = self.sentence_splitter.split_sentences(text_content)
        if not sentences:
            return [create_chunk(text_content, self.token_counter.count_tokens(text_content), header_path, parent_section, "text")]
        
        chunks, current_sentences, current_tokens = [], [], 0
        
        for sentence in sentences:
            sentence_tokens = self.token_counter.count_tokens(sentence)
            
            if sentence_tokens > self.max_chunk_size:
                if current_sentences:
                    chunks.append(create_chunk(" ".join(current_sentences), current_tokens, header_path, parent_section, "text"))
                chunks.append(create_chunk(sentence, sentence_tokens, header_path, parent_section, "text"))
                current_sentences, current_tokens = [], 0
                continue
            
            if current_tokens + sentence_tokens > self.max_chunk_size and current_sentences:
                chunks.append(create_chunk(" ".join(current_sentences), current_tokens, header_path, parent_section, "text"))
                current_sentences, current_tokens = [sentence], sentence_tokens
            else:
                current_sentences.append(sentence)
                current_tokens += sentence_tokens
        
        if current_sentences:
            chunks.append(create_chunk(" ".join(current_sentences), current_tokens, header_path, parent_section, "text"))
        return chunks