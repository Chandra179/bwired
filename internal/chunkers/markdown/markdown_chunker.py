"""Markdown-specific document chunker with integrated section analysis"""
from typing import List, Dict
import logging
import re

from ..base_chunker import BaseDocumentChunker
from .markdown_parser import MarkdownParser, MarkdownElement, ElementType
from .section_analyzer import SectionAnalyzer, Section
from .overlap_handler import OverlapHandler
from .table_splitter import TableSplitter
from .code_splitter import CodeSplitter
from .list_splitter import ListSplitter
from .text_splitter import TextSplitter
from ...text_processing.sentence_splitter import SentenceSplitter
from ...text_processing.tokenizer_utils import TokenCounter
from ...config import RAGChunkingConfig
from ..schema import SemanticChunk

logger = logging.getLogger(__name__)


class MarkdownDocumentChunker(BaseDocumentChunker):
    """
    RAG-optimized markdown chunker with:
    - Semantic section hierarchy
    - Sliding window overlap
    - Relationship tracking
    - Enhanced ancestry paths
    """
    
    def __init__(self, config: RAGChunkingConfig):
        super().__init__(config)
        
        self.parser = MarkdownParser()
        self.section_analyzer = SectionAnalyzer()
        self.sentence_splitter = SentenceSplitter()
        self.token_counter = TokenCounter(config.embedding.dense.model_name)
        self.overlap_handler = OverlapHandler(self.sentence_splitter)
        
        # Initialize markdown-specific splitters
        self.table_splitter = TableSplitter(config, self.sentence_splitter, self.token_counter)
        self.code_splitter = CodeSplitter(config, self.sentence_splitter, self.token_counter)
        self.list_splitter = ListSplitter(config, self.sentence_splitter, self.token_counter)
        self.text_splitter = TextSplitter(config, self.sentence_splitter, self.token_counter)
        
        logger.info("MarkdownDocumentChunker initialized with overlap and relationship tracking")
    
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
            List of semantic chunks with overlap and relationships
        """
        logger.info(f"Processing document: {document_id}")
        
        # Stage 1: Parse markdown into elements
        elements = self.parser.parse(content)
        logger.info(f"Stage 1: Parsed {len(elements)} elements")
        
        # Stage 2: Build section hierarchy
        sections = self.section_analyzer.analyze(elements)
        logger.info(f"Stage 2: Extracted {len(sections)} top-level sections")
        
        # Stage 3: Chunk sections
        all_chunks = []
        for section in sections:
            section_chunks = self._chunk_section(section, ancestry=[])
            all_chunks.extend(section_chunks)
        
        logger.info(f"Stage 3: Created {len(all_chunks)} semantic chunks")
        
        # Stage 4: Apply overlap
        all_chunks = self._apply_overlap_by_section(all_chunks)
        logger.info(f"Stage 4: Applied overlap to chunks")
        
        return all_chunks
    
    def _chunk_section(
        self, 
        section: Section,
        ancestry: List[str]
    ) -> List[SemanticChunk]:
        """Chunk a section with enhanced ancestry tracking"""
        chunks = []
        
        current_ancestry = ancestry + [section.heading.content] if section.heading else ancestry
        header_path = " > ".join(current_ancestry)
        
        buffer_elements = []
        buffer_tokens = 0
        
        max_size = self.config.chunking.max_chunk_size

        for element in section.content_elements:
            if self._is_metadata_noise(element.content):
                continue
            
            element_tokens = self.token_counter.count_tokens(element.content)
            
            # Handle large/special elements individually
            if element_tokens > max_size or element.type in [ElementType.CODE_BLOCK, ElementType.TABLE]:
                if buffer_elements:
                    chunks.append(self._create_chunk_from_buffer(buffer_elements, header_path))
                    buffer_elements = []
                    buffer_tokens = 0
                
                chunks.extend(self._chunk_element(element, header_path))
                
            # Element fits in buffer
            elif buffer_tokens + element_tokens <= max_size:
                buffer_elements.append(element)
                buffer_tokens += element_tokens
                
            # Buffer full, flush and start new
            else:
                chunks.append(self._create_chunk_from_buffer(buffer_elements, header_path))
                buffer_elements = [element]
                buffer_tokens = element_tokens
                
        # Flush remaining buffer
        if buffer_elements:
            chunks.append(self._create_chunk_from_buffer(buffer_elements, header_path))
        
        # Recursively process subsections with updated ancestry
        for subsection in section.subsections:
            chunks.extend(self._chunk_section(subsection, current_ancestry))
        
        return chunks
    
    def _create_chunk_from_buffer(
        self, 
        elements: List[MarkdownElement], 
        header_path: str
    ) -> SemanticChunk:
        """Helper to merge multiple small elements into one coherent chunk"""
        combined_content = "\n\n".join([e.content for e in elements])
        return SemanticChunk(
            content=combined_content,
            token_count=self.token_counter.count_tokens(combined_content),
            chunk_type="text",
            section_path=header_path,
            is_continuation=False,
            split_sequence=None
        )
    
    def _chunk_element(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """
        Chunk a single element based on type using specific splitters
        """
        if element.type in (ElementType.PARAGRAPH, ElementType.HEADING):
            if self._is_metadata_noise(element.content):
                return []
        
        chunks = []
        
        if element.type == ElementType.TABLE:
            chunks = self.table_splitter.chunk(element, header_path)
        
        elif element.type == ElementType.CODE_BLOCK:
            chunks = self.code_splitter.chunk(element, header_path)
        
        elif element.type == ElementType.LIST:
            chunks = self.list_splitter.chunk(element, header_path)
        
        elif element.type == ElementType.PARAGRAPH:
            chunks = self.text_splitter.chunk(element, header_path)
        
        elif element.type == ElementType.HEADING:
            # Only chunk significant headings
            token_count = self.token_counter.count_tokens(element.content)
            if token_count > 50:
                chunks = self.text_splitter.chunk(element, header_path)
            else:
                chunks = []
        
        else:
            # Default fallback
            chunks = self.text_splitter.chunk(element, header_path)
            
        return chunks
    
    def _apply_overlap_by_section(self, chunks: List[SemanticChunk]) -> List[SemanticChunk]:
        """
        Apply overlap to chunks, but only within same section
        """
        if self.config.chunking.overlap_tokens <= 0:
            return chunks
        
        # Group chunks by section_path
        section_groups: Dict[str, List[SemanticChunk]] = {}
        for chunk in chunks:
            section_path = chunk.section_path
            if section_path not in section_groups:
                section_groups[section_path] = []
            section_groups[section_path].append(chunk)
        
        # Apply overlap within each section group
        result = []
        for section_path, section_chunks in section_groups.items():
            overlapped = self.overlap_handler.apply_overlap(
                section_chunks,
                self.config.chunking.overlap_tokens,
                self.token_counter,
                self.config.embedding.embedding_token_limit,
            )
            result.extend(overlapped)
        
        return result
    
    def _is_metadata_noise(self, text: str) -> bool:
        """
        Detect non-content sections like references, bibliographies, TOCs
        """
        if not text or len(text) < 20:
            return False
        
        text_lower = text.lower()
        
        # Explicit section markers
        noise_markers = [
            'references\n', 'bibliography\n', 'notes\n', 
            'acknowledgement', 'acknowledgment',
            'table of contents', 'list of figures',
            'appendix', 'glossary'
        ]
        if any(marker in text_lower[:100] for marker in noise_markers):
            return True
        
        # Citation pattern detection
        citation_patterns = [
            r'\([12]\d{3}\)',  # (2004), (1999)
            r'[A-Z][a-z]+,?\s+[A-Z]\.',  # Author, N. or Author N.
            r'et al\.',  # et al.
        ]
        matches = sum(len(re.findall(pattern, text)) for pattern in citation_patterns)
        if matches > 3:
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