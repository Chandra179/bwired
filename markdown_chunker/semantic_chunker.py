"""
Semantic chunking orchestrator - combines all stages
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

from .parser import MarkdownParser, MarkdownElement, ElementType
from .section_analyzer import SectionAnalyzer, Section
from .sentence_splitter import SentenceSplitter
from .context_enricher import ContextEnricher
from .tokenizer_utils import TokenCounter
from .config import RAGChunkingConfig

logger = logging.getLogger(__name__)


@dataclass
class SemanticChunk:
    """Represents a semantically meaningful chunk for RAG"""
    content: str
    original_content: str  # Before context enrichment
    token_count: int
    chunk_type: str
    chunk_index: int
    
    # Hierarchy
    section_path: str  # Full hierarchical path (e.g., "Introduction > Getting Started > Installation")
    section_level: int
    
    # RAG metadata
    entities: Optional[Dict[str, List[str]]] = None
    
    # Multi-representation
    has_multi_representation: bool = False
    natural_language_description: Optional[str] = None
    representations: Optional[Dict[str, str]] = None
    
    # Additional metadata
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Optimization: Direct reference to source element (Excluded from serialization/repr)
    # This enables O(1) access to metadata without searching
    source_element: Optional[MarkdownElement] = field(default=None, repr=False)


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
        self.context_enricher = ContextEnricher(config.context)
        self.token_counter = TokenCounter(config.embedding.model_name)
        
        logger.info("SemanticChunker initialized with RAG optimizations")
    
    def chunk_document(
        self, 
        content: str, 
        document_id: str, 
        document_title: str = ""
    ) -> List[SemanticChunk]:
        """
        Chunk markdown document with semantic awareness
        
        Args:
            content: Markdown content
            document_id: Unique document identifier
            document_title: Document title
            
        Returns:
            List of semantic chunks
        """
        logger.info(f"Processing document: {document_id}")
        
        elements = self.parser.parse(content)
        logger.info(f"Stage 1: Parsed {len(elements)} elements")
        
        sections = self.section_analyzer.analyze(elements)
        logger.info(f"Stage 2: Extracted {len(sections)} top-level sections")
        
        chunks = []
        chunk_index = 0
        
        for section in sections:
            section_chunks = self._chunk_section(section, document_title)
            
            # Assign indices
            for chunk in section_chunks:
                chunk.chunk_index = chunk_index
                chunk_index += 1
            
            chunks.extend(section_chunks)
        
        logger.info(f"Stage 3: Created {len(chunks)} semantic chunks")
        
        chunks = self._enhance_chunks(chunks, document_title)
        logger.info(f"Stage 4: Enhanced {len(chunks)} chunks with context")
        
        return chunks
    
    def _chunk_section(
        self, 
        section: Section, 
        document_title: str
    ) -> List[SemanticChunk]:
        """
        Chunk a single section hierarchically
        
        Args:
            section: Section to chunk
            document_title: Document title
            
        Returns:
            List of chunks for this section
        """
        chunks = []
        header_path = section.get_header_path()
        
        # Process content elements in this section
        for element in section.content_elements:
            element_chunks = self._chunk_element(
                element, 
                header_path,
                section.level
            )
            chunks.extend(element_chunks)
        
        # Recursively process subsections
        for subsection in section.subsections:
            subsection_chunks = self._chunk_section(subsection, document_title)
            chunks.extend(subsection_chunks)
        
        return chunks
    
    def _chunk_element(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
    ) -> List[SemanticChunk]:
        """
        Chunk a single element based on type and inject source reference
        """
        generated_chunks = []

        if element.type == ElementType.TABLE:
            generated_chunks = self._chunk_table(element, header_path, section_level)
        
        elif element.type == ElementType.CODE_BLOCK:
            generated_chunks = self._chunk_code(element, header_path, section_level)
        
        elif element.type == ElementType.LIST:
            generated_chunks = self._chunk_list(element, header_path, section_level)
        
        elif element.type == ElementType.PARAGRAPH:
            generated_chunks = self._chunk_text(element, header_path, section_level)
        
        elif element.type == ElementType.HEADING:
            # Only chunk significant headings
            token_count = self.token_counter.count_tokens(element.content)
            if token_count > 50:
                generated_chunks = self._chunk_text(element, header_path, section_level)
            else:
                generated_chunks = []
        
        else:
            generated_chunks = self._chunk_text(element, header_path, section_level)

        # CRITICAL OPTIMIZATION: Attach source element reference here
        # This avoids the O(N^2) search in Stage 4
        for chunk in generated_chunks:
            chunk.source_element = element
            
        return generated_chunks
    
    def _chunk_table(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
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
                original_content=content,
                token_count=token_count,
                chunk_type="table",
                chunk_index=0,
                section_path=header_path,
                section_level=section_level,
                extra_metadata=element.metadata
            )]
        
        # Table is too large and splitting allowed
        return self._split_table_by_rows(element, header_path, section_level)
    
    def _split_table_by_rows(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
    ) -> List[SemanticChunk]:
        """Split large table by rows"""
        lines = element.content.split('\n')
        
        if len(lines) < 3:
            # Too small to split
            return self._chunk_table(element, header_path, section_level)
        
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
                        original_content=table_chunk,
                        token_count=self.token_counter.count_tokens(table_chunk),
                        chunk_type="table",
                        chunk_index=len(chunks),
                        section_path=header_path,
                        section_level=section_level,
                        extra_metadata={
                            **element.metadata,
                            'is_partial_table': True
                        }
                    ))
                
                current_rows = [row]
                current_tokens = row_tokens
        
        # Add remaining
        if current_rows:
            table_chunk = '\n'.join([header_row, separator] + current_rows)
            chunks.append(SemanticChunk(
                content=table_chunk,
                original_content=table_chunk,
                token_count=self.token_counter.count_tokens(table_chunk),
                chunk_type="table",
                chunk_index=len(chunks),
                section_path=header_path,
                section_level=section_level,
                extra_metadata={
                    **element.metadata,
                    'is_partial_table': True
                }
            ))
        
        return chunks
    
    def _chunk_code(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
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
                original_content=content,
                token_count=token_count,
                chunk_type="code_block",
                chunk_index=0,
                section_path=header_path,
                section_level=section_level,
                extra_metadata=element.metadata
            )]
        
        # Code too large - split by lines
        return self._split_code_by_lines(element, header_path, section_level)
    
    def _split_code_by_lines(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
    ) -> List[SemanticChunk]:
        """Split code by lines when too large"""
        lines = element.content.split('\n')
        chunks = []
        current_lines = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = self.token_counter.count_tokens(line)
            
            if current_tokens + line_tokens <= self.config.chunking.target_chunk_size:
                current_lines.append(line)
                current_tokens += line_tokens
            else:
                if current_lines:
                    code_chunk = '\n'.join(current_lines)
                    chunks.append(SemanticChunk(
                        content=code_chunk,
                        original_content=code_chunk,
                        token_count=self.token_counter.count_tokens(code_chunk),
                        chunk_type="code_block",
                        chunk_index=len(chunks),
                        section_path=header_path,
                        section_level=section_level,
                        extra_metadata={
                            **element.metadata,
                            'is_partial_code': True
                        }
                    ))
                
                current_lines = [line]
                current_tokens = line_tokens
        
        if current_lines:
            code_chunk = '\n'.join(current_lines)
            chunks.append(SemanticChunk(
                content=code_chunk,
                original_content=code_chunk,
                token_count=self.token_counter.count_tokens(code_chunk),
                chunk_type="code_block",
                chunk_index=len(chunks),
                section_path=header_path,
                section_level=section_level,
                extra_metadata={
                    **element.metadata,
                    'is_partial_code': True
                }
            ))
        
        return chunks
    
    def _chunk_list(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
    ) -> List[SemanticChunk]:
        """Chunk list - keep items together"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # If list fits, keep whole
        if token_count <= self.config.chunking.target_chunk_size:
            return [SemanticChunk(
                content=element.content,
                original_content=element.content,
                token_count=token_count,
                chunk_type="list",
                chunk_index=0,
                section_path=header_path,
                section_level=section_level,
                extra_metadata=element.metadata
            )]
        
        # Split by items
        if self.config.chunking.keep_list_items_together:
            return self._split_list_by_items(element, header_path, section_level)
        else:
            # Treat as text
            return self._chunk_text(element, header_path, section_level)
    
    def _split_list_by_items(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
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
                        original_content=list_chunk,
                        token_count=self.token_counter.count_tokens(list_chunk),
                        chunk_type="list",
                        chunk_index=len(chunks),
                        section_path=header_path,
                        section_level=section_level,
                        extra_metadata=element.metadata
                    ))
                
                current_items = [line]
                current_tokens = line_tokens
        
        if current_items:
            list_chunk = '\n'.join(current_items)
            chunks.append(SemanticChunk(
                content=list_chunk,
                original_content=list_chunk,
                token_count=self.token_counter.count_tokens(list_chunk),
                chunk_type="list",
                chunk_index=len(chunks),
                section_path=header_path,
                section_level=section_level,
                extra_metadata=element.metadata
            ))
        
        return chunks
    
    def _chunk_text(
        self,
        element: MarkdownElement,
        header_path: str,
        section_level: int
    ) -> List[SemanticChunk]:
        """Chunk text/paragraph with sentence awareness"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # If fits in one chunk
        if token_count <= self.config.chunking.target_chunk_size:
            return [SemanticChunk(
                content=element.content,
                original_content=element.content,
                token_count=token_count,
                chunk_type=element.type.value,
                chunk_index=0,
                section_path=header_path,
                section_level=section_level,
                extra_metadata=element.metadata
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
                original_content=text_chunk,
                token_count=self.token_counter.count_tokens(text_chunk),
                chunk_type=element.type.value,
                chunk_index=i,
                section_path=header_path,
                section_level=section_level,
                extra_metadata=element.metadata
            ))
        
        return chunks
    
    def _enhance_chunks(
        self,
        chunks: List[SemanticChunk],
        document_title: str
    ) -> List[SemanticChunk]:
        """
        Stage 4: O(N) Context Enhancement
        Eliminates redundant sentence splitting and searching.
        """
        enhanced_chunks = []
        cfg = self.config.context
        
        # 1. Pre-calculate sentences for all chunks (Single Pass)
        # This acts as a cache so we don't re-split text for neighbors
        chunk_sentences_map = []
        needs_context = cfg.surrounding_sentences_before > 0 or cfg.surrounding_sentences_after > 0
        
        if needs_context:
            for chunk in chunks:
                chunk_sentences_map.append(
                    self.sentence_splitter.split_sentences(chunk.original_content)
                )
        
        total_chunks = len(chunks)

        # 2. Single Loop Enhancement
        for i, chunk in enumerate(chunks):
            context = {}
            
            if needs_context:
                # Optimized Context Before (Lookup, no splitting)
                if cfg.surrounding_sentences_before > 0 and i > 0:
                    prev_sentences = []
                    # Look back up to 3 chunks purely for sentences
                    lookback_start = max(0, i - 3)
                    for j in range(i - 1, lookback_start - 1, -1):
                        prev_sentences = chunk_sentences_map[j] + prev_sentences
                        if len(prev_sentences) >= cfg.surrounding_sentences_before:
                            break
                    
                    if prev_sentences:
                        relevant = prev_sentences[-cfg.surrounding_sentences_before:]
                        context['before'] = ' '.join(relevant)
                
                # Optimized Context After (Lookup, no splitting)
                if cfg.surrounding_sentences_after > 0 and i < total_chunks - 1:
                    next_sentences = []
                    lookahead_end = min(total_chunks, i + 3)
                    for j in range(i + 1, lookahead_end):
                        next_sentences.extend(chunk_sentences_map[j])
                        if len(next_sentences) >= cfg.surrounding_sentences_after:
                            break
                    
                    if next_sentences:
                        relevant = next_sentences[:cfg.surrounding_sentences_after]
                        context['after'] = ' '.join(relevant)
            
            # 3. Direct Element Access (O(1))
            # We use the reference stored in Stage 3
            element = chunk.source_element
            
            # Enrich
            enriched = self.context_enricher.enrich_chunk(
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                header_path=chunk.section_path,
                document_title=document_title,
                element=element,
                surrounding_context=context
            )
            
            # Update fields
            chunk.content = enriched['content']
            chunk.token_count = self.token_counter.count_tokens(chunk.content)
            
            if 'entities' in enriched.get('metadata', {}):
                chunk.entities = enriched['metadata']['entities']
            
            if 'representations' in enriched:
                chunk.has_multi_representation = True
                chunk.representations = enriched['representations']
                # Prefer explicit descriptions if available
                chunk.natural_language_description = (
                    enriched['metadata'].get('table_description') or 
                    enriched['metadata'].get('code_description')
                )
            
            enhanced_chunks.append(chunk)
        
        return enhanced_chunks
    
    def _get_surrounding_context(
        self,
        chunks: List[SemanticChunk],
        index: int
    ) -> Dict[str, str]:
        """Get context from surrounding chunks"""
        context = {}
        
        cfg = self.config.context
        
        # Get sentences from previous chunks
        if cfg.surrounding_sentences_before > 0 and index > 0:
            prev_sentences = []
            for i in range(max(0, index - 3), index):
                sentences = self.sentence_splitter.split_sentences(
                    chunks[i].original_content
                )
                prev_sentences.extend(sentences)
            
            if prev_sentences:
                context['before'] = ' '.join(prev_sentences[-cfg.surrounding_sentences_before:])
        
        # Get sentences from next chunks
        if cfg.surrounding_sentences_after > 0 and index < len(chunks) - 1:
            next_sentences = []
            for i in range(index + 1, min(len(chunks), index + 3)):
                sentences = self.sentence_splitter.split_sentences(
                    chunks[i].original_content
                )
                next_sentences.extend(sentences)
            
            if next_sentences:
                context['after'] = ' '.join(next_sentences[:cfg.surrounding_sentences_after])
        
        return context
    
    def _find_element_for_chunk(
        self,
        chunk: SemanticChunk,
        elements: List[MarkdownElement]
    ) -> Optional[MarkdownElement]:
        """Find the original element that generated this chunk by matching content"""
        for element in elements:
            # Match by content similarity since we no longer have line numbers
            if element.content.strip() in chunk.original_content.strip() or \
               chunk.original_content.strip() in element.content.strip():
                return element
        return None