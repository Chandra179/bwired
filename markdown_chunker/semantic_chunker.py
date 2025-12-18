from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging

from .parser import MarkdownParser, MarkdownElement, ElementType
from .section_analyzer import SectionAnalyzer, Section
from .sentence_splitter import SentenceSplitter
from .tokenizer_utils import TokenCounter
from .config import RAGChunkingConfig

logger = logging.getLogger(__name__)


@dataclass
class SemanticChunk:
    """Represents a semantically meaningful chunk for RAG"""
    content: str
    token_count: int
    chunk_type: str
    
    section_path: str  # Full hierarchical path (e.g., "Introduction > Getting Started > Installation")
    
    # Direct reference to source element (Excluded from serialization/repr)
    # This enables O(1) access to metadata without searching
    source_element: Optional[MarkdownElement] = field(default=None, repr=False)
    
    # Sticky Context (for split code/tables)
    contextual_header: Optional[str] = None  # e.g., "function process_data(...) {"

class SemanticChunker:
    """
    RAG-optimized semantic chunker
    
    Combines:
    - Stage 1: Parsing (markdown-it-py)
    - Stage 2: Section Analysis
    - Stage 3: Semantic Chunking
    - Stage 4: Context Enhancement
    """
    
    def __init__(self, config: RAGChunkingConfig):
        self.config = config
        
        self.parser = MarkdownParser()
        self.section_analyzer = SectionAnalyzer()
        self.sentence_splitter = SentenceSplitter()
        self.token_counter = TokenCounter(config.embedding.model_name)
        
        logger.info("SemanticChunker initialized with RAG optimizations")
    
    def chunk_document(
        self, 
        content: str, 
        document_id: str,
    ) -> List[SemanticChunk]:
        """
        Chunk markdown document with semantic awareness
        
        Args:
            content: Markdown content
            document_id: Unique document identifier
            
        Returns:
            List of semantic chunks
        """
        logger.info(f"Processing document: {document_id}")
        
        elements = self.parser.parse(content)
        logger.info(f"Stage 1: Parsed {len(elements)} elements")
        
        sections = self.section_analyzer.analyze(elements)
        logger.info(f"Stage 2: Extracted {len(sections)} top-level sections")
        
        chunks = []
        
        for section in sections:
            section_chunks = self._chunk_section(section)
            
            chunks.extend(section_chunks)
        logger.info(f"Stage 3: Created {len(chunks)} semantic chunks")
        
        return chunks
    
    def _chunk_section(
        self, 
        section: Section
    ) -> List[SemanticChunk]:
        chunks = []
        header_path = section.get_header_path()
        
        buffer_elements = []
        buffer_tokens = 0
        target_size = self.config.chunking.target_chunk_size

        for element in section.content_elements:
            if self._is_metadata_noise(element.content):
                continue
            
            element_tokens = self.token_counter.count_tokens(element.content)
            
            # If element is huge (Code Block / Table > target), flush buffer first
            if element_tokens > target_size or element.type in [ElementType.CODE_BLOCK, ElementType.TABLE]:
                if buffer_elements:
                    chunks.append(self._create_chunk_from_buffer(buffer_elements, header_path))
                    buffer_elements = []
                    buffer_tokens = 0
                
                # Process the large/special element individually
                chunks.extend(self._chunk_element(element, header_path))
                
            # If adding this element fits in the chunk, add to buffer
            elif buffer_tokens + element_tokens <= target_size:
                buffer_elements.append(element)
                buffer_tokens += element_tokens
                
            # Buffer is full, flush and start new
            else:
                chunks.append(self._create_chunk_from_buffer(buffer_elements, header_path))
                buffer_elements = [element]
                buffer_tokens = element_tokens
                
        # Flush remaining buffer
        if buffer_elements:
            chunks.append(self._create_chunk_from_buffer(buffer_elements, header_path))
        
        # Recursively process subsections
        for subsection in section.subsections:
            chunks.extend(self._chunk_section(subsection))
        
        return chunks
    
    def _create_chunk_from_buffer(self, elements: List[MarkdownElement], header_path: str) -> SemanticChunk:
        """Helper to merge multiple small elements into one coherent chunk"""
        combined_content = "\n\n".join([e.content for e in elements])
        return SemanticChunk(
            content=combined_content,
            token_count=self.token_counter.count_tokens(combined_content),
            chunk_type="text", # Generalized type
            section_path=header_path,
            source_element=elements[0] if elements else None
        )
    
    def _chunk_element(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """
        Chunk a single element based on type and inject source reference
        """
        generated_chunks = []

        if element.type in (ElementType.PARAGRAPH, ElementType.HEADING):
            if self._is_metadata_noise(element.content):
                return []
            
        if element.type == ElementType.TABLE:
            generated_chunks = self._chunk_table(element, header_path)
        
        elif element.type == ElementType.CODE_BLOCK:
            generated_chunks = self._chunk_code(element, header_path)
        
        elif element.type == ElementType.LIST:
            generated_chunks = self._chunk_list(element, header_path)
        
        elif element.type == ElementType.PARAGRAPH:
            generated_chunks = self._chunk_text(element, header_path)
        
        elif element.type == ElementType.HEADING:
            # Only chunk significant headings
            token_count = self.token_counter.count_tokens(element.content)
            if token_count > 50:
                generated_chunks = self._chunk_text(element, header_path)
            else:
                generated_chunks = []
        
        else:
            generated_chunks = self._chunk_text(element, header_path)

        for chunk in generated_chunks:
            chunk.source_element = element
            
        return generated_chunks
    
    def _chunk_table(
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
                section_path=header_path
            )]
        
        # Table is too large and splitting allowed
        return self._split_table_by_rows(element, header_path)
    
    def _split_table_by_rows(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Split large table by rows"""
        lines = element.content.split('\n')
        
        if len(lines) < 3:
            # Too small to split
            return self._chunk_table(element, header_path)
        
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
                        section_path=header_path
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
                section_path=header_path
            ))
        
        return chunks
    
    def _chunk_code(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Chunk code block - keep intact if possible"""
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
                section_path=header_path
            )]
        
        # Code too large - split by lines
        return self._split_code_by_lines(element, header_path)
    
    def _split_code_by_lines(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        lines = element.content.split('\n')
        chunks = []
        current_lines = []
        
        # Identify Sticky Header (Naive approach: First non-empty line)
        # In production, use regex to find 'def', 'class', 'func'
        sticky_header = next((line for line in lines if line.strip()), "")
        
        current_tokens = self.token_counter.count_tokens(sticky_header)
        
        # Start loop skipping the sticky header if we added it
        start_index = 1 if lines[0] == sticky_header else 0
        
        for line in lines[start_index:]:
            line_tokens = self.token_counter.count_tokens(line)
            
            if current_tokens + line_tokens <= self.config.chunking.target_chunk_size:
                current_lines.append(line)
                current_tokens += line_tokens
            else:
                # Flush Chunk
                if current_lines:
                    # Prepend sticky header to the chunk content if it's not the first chunk
                    # Or store it in metadata for the LLM to see contextually
                    chunk_content = '\n'.join(current_lines)
                    
                    chunks.append(SemanticChunk(
                        content=chunk_content,
                        token_count=current_tokens,
                        chunk_type="code_block",
                        section_path=header_path,
                        contextual_header=sticky_header if len(chunks) > 0 else None
                    ))
                
                current_lines = [line]
                current_tokens = line_tokens + self.token_counter.count_tokens(sticky_header)

        return chunks
    
    def _chunk_list(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Chunk list - keep items together"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # If list fits, keep whole
        if token_count <= self.config.chunking.target_chunk_size:
            return [SemanticChunk(
                content=element.content,
                token_count=token_count,
                chunk_type="list",
                section_path=header_path
            )]
        
        if self.config.chunking.keep_list_items_together:
            return self._split_list_by_items(element, header_path)
        else:
            # Treat as text
            return self._chunk_text(element, header_path)
    
    def _split_list_by_items(
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
                        section_path=header_path
                    ))
                
                current_items = [line]
                current_tokens = line_tokens
        
        if current_items:
            list_chunk = '\n'.join(current_items)
            chunks.append(SemanticChunk(
                content=list_chunk,
                token_count=self.token_counter.count_tokens(list_chunk),
                chunk_type="list",
                section_path=header_path
            ))
        
        return chunks
    
    def _chunk_text(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """Chunk text/paragraph with sentence awareness"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # If fits in one chunk
        if token_count <= self.config.chunking.target_chunk_size:
            return [SemanticChunk(
                content=element.content,
                token_count=token_count,
                chunk_type=element.type.value,
                section_path=header_path
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
            text_chunks = [element.content]  # Would need word-based splitter
        
        chunks = []
        for i, text_chunk in enumerate(text_chunks):
            chunks.append(SemanticChunk(
                content=text_chunk,
                token_count=self.token_counter.count_tokens(text_chunk),
                chunk_type=element.type.value,
                section_path=header_path
            ))
        
        return chunks
    
    def _is_metadata_noise(self, text: str) -> bool:
        """
        Detect non-content sections like references, bibliographies, TOCs
        """
        if not text or len(text) < 20:
            return False
        
        text_lower = text.lower()
        
        # Explicit section markers (most reliable)
        noise_markers = [
            'references\n', 'bibliography\n', 'notes\n', 
            'acknowledgement', 'acknowledgment',
            'table of contents', 'list of figures',
            'appendix', 'glossary'
        ]
        if any(marker in text_lower[:100] for marker in noise_markers):
            return True
        
        # Citation pattern detection
        # Look for multiple citations like "Author (Year)" or "Author, Year"
        import re
        citation_patterns = [
            r'\([12]\d{3}\)',  # (2004), (1999)
            r'[A-Z][a-z]+,?\s+[A-Z]\.',  # Author, N. or Author N.
            r'et al\.',  # et al.
        ]
        matches = sum(len(re.findall(pattern, text)) for pattern in citation_patterns)
        if matches > 3:  # Multiple citations = likely references
            return True
        
        words = text.split()
        if not words:
            return True
        
        cap_words = [w for w in words if w and w[0].isupper()]
        cap_ratio = len(cap_words) / len(words)
        
        if cap_ratio > 0.6:
            common_verbs = {'is', 'are', 'was', 'were', 'has', 'have', 
                        'can', 'will', 'shows', 'indicates', 'describes'}
            has_verbs = any(v in text_lower.split() for v in common_verbs)
            if not has_verbs:
                return True
        
        return False