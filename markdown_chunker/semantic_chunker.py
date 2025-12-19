from typing import List, Dict
import logging
import re

from .parser import MarkdownParser, MarkdownElement, ElementType
from .section_analyzer import SectionAnalyzer, Section
from .sentence_splitter import SentenceSplitter
from .tokenizer_utils import TokenCounter
from .config import RAGChunkingConfig
from .overlap_handler import OverlapHandler
from .chunk_splitters import ChunkSplitters
from .schema import SemanticChunk

logger = logging.getLogger(__name__)

class SemanticChunker:
    """
    RAG-optimized semantic chunker with:
    - Sliding window overlap
    - Relationship tracking
    - Enhanced ancestry paths
    """
    
    def __init__(self, config: RAGChunkingConfig):
        self.config = config
        
        self.parser = MarkdownParser()
        self.section_analyzer = SectionAnalyzer()
        self.sentence_splitter = SentenceSplitter()
        self.token_counter = TokenCounter(config.embedding.model_name)
        self.overlap_handler = OverlapHandler(self.sentence_splitter)
        self.splitters = ChunkSplitters(config, self.sentence_splitter, self.token_counter)
        
        logger.info("SemanticChunker initialized with overlap and relationship tracking")
    
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
        
        elements = self.parser.parse(content)
        logger.info(f"Stage 1: Parsed {len(elements)} elements")
        
        sections = self.section_analyzer.analyze(elements)
        logger.info(f"Stage 2: Extracted {len(sections)} top-level sections")
        
        all_chunks = []
        
        for section in sections:
            section_chunks = self._chunk_section(section, ancestry=[])
            all_chunks.extend(section_chunks)
        
        logger.info(f"Stage 3: Created {len(all_chunks)} semantic chunks")
        
        all_chunks = self._apply_overlap_by_section(all_chunks)
        logger.info(f"Stage 4: Applied overlap to chunks")
        
        return all_chunks
    
    def _chunk_section(
        self, 
        section: Section,
        ancestry: List[str]
    ) -> List[SemanticChunk]:
        """
        Chunk a section with enhanced ancestry tracking
        
        Args:
            section: Section to chunk
            ancestry: List of ancestor heading texts
            
        Returns:
            List of chunks from this section and subsections
        """
        chunks = []
        
        current_ancestry = ancestry + [section.heading.content] if section.heading else ancestry
        header_path = " > ".join(current_ancestry)
        
        buffer_elements = []
        buffer_tokens = 0
        
        soft_limit = self.config.chunking.effective_target_size

        for element in section.content_elements:
            if self._is_metadata_noise(element.content):
                continue
            
            element_tokens = self.token_counter.count_tokens(element.content)
            
            # Handle large/special elements individually
            if element_tokens > soft_limit or element.type in [ElementType.CODE_BLOCK, ElementType.TABLE]:
                if buffer_elements:
                    chunks.append(self._create_chunk_from_buffer(buffer_elements, header_path))
                    buffer_elements = []
                    buffer_tokens = 0
                
                chunks.extend(self._chunk_element(element, header_path))
                
            # Element fits in buffer
            elif buffer_tokens + element_tokens <= soft_limit:
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
            source_element=elements[0] if elements else None,
            is_continuation=False,
            split_sequence=None
        )
    
    def _chunk_element(
        self,
        element: MarkdownElement,
        header_path: str
    ) -> List[SemanticChunk]:
        """
        Chunk a single element based on type
        """
        if element.type in (ElementType.PARAGRAPH, ElementType.HEADING):
            if self._is_metadata_noise(element.content):
                return []
        
        if element.type == ElementType.TABLE:
            chunks = self.splitters.chunk_table(element, header_path)
        
        elif element.type == ElementType.CODE_BLOCK:
            chunks = self.splitters.chunk_code(element, header_path)
        
        elif element.type == ElementType.LIST:
            chunks = self.splitters.chunk_list(element, header_path)
        
        elif element.type == ElementType.PARAGRAPH:
            chunks = self.splitters.chunk_text(element, header_path)
        
        elif element.type == ElementType.HEADING:
            # Only chunk significant headings
            token_count = self.token_counter.count_tokens(element.content)
            if token_count > 50:
                chunks = self.splitters.chunk_text(element, header_path)
            else:
                chunks = []
        
        else:
            chunks = self.splitters.chunk_text(element, header_path)

        # Inject source element reference
        for chunk in chunks:
            chunk.source_element = element
            
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
                self.config.chunking.target_chunk_size,
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