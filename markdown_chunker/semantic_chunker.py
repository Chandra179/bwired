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
    original_content: str
    token_count: int
    chunk_type: str
    chunk_index: int
    
    section_path: str  # Full hierarchical path (e.g., "Introduction > Getting Started > Installation")
    
    # Direct reference to source element (Excluded from serialization/repr)
    # This enables O(1) access to metadata without searching
    source_element: Optional[MarkdownElement] = field(default=None, repr=False)
    
    # Search: "Config > Rate Limit \n Context: API... \n The limit is 50."
    search_content: Optional[str] = None 
    
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
        self.context_enricher = ContextEnricher(config.context)
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
        chunk_index = 0
        
        for section in sections:
            section_chunks = self._chunk_section(section)
            
            # Assign indices
            for chunk in section_chunks:
                chunk.chunk_index = chunk_index
                chunk_index += 1
            
            chunks.extend(section_chunks)
        logger.info(f"Stage 3: Created {len(chunks)} semantic chunks")
        
        chunks = self._enhance_chunks(chunks)
        logger.info(f"Stage 4: Enhanced {len(chunks)} chunks with context")
        
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
            # Skip meaningful noise (optional, keep your existing logic)
            if self._is_metadata_noise(element.content):
                continue
            
            # Calculate size
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
            original_content=combined_content,
            token_count=self.token_counter.count_tokens(combined_content),
            chunk_type="text", # Generalized type
            chunk_index=0,     # Will be set later
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
                original_content=content,
                token_count=token_count,
                chunk_type="table",
                chunk_index=0,
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
                        original_content=table_chunk,
                        token_count=self.token_counter.count_tokens(table_chunk),
                        chunk_type="table",
                        chunk_index=len(chunks),
                        section_path=header_path
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
                original_content=content,
                token_count=token_count,
                chunk_type="code_block",
                chunk_index=0,
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
                        original_content=chunk_content,
                        token_count=current_tokens,
                        chunk_type="code_block",
                        chunk_index=len(chunks),
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
                original_content=element.content,
                token_count=token_count,
                chunk_type="list",
                chunk_index=0,
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
                        original_content=list_chunk,
                        token_count=self.token_counter.count_tokens(list_chunk),
                        chunk_type="list",
                        chunk_index=len(chunks),
                        section_path=header_path
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
                original_content=element.content,
                token_count=token_count,
                chunk_type=element.type.value,
                chunk_index=0,
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
                original_content=text_chunk,
                token_count=self.token_counter.count_tokens(text_chunk),
                chunk_type=element.type.value,
                chunk_index=i,
                section_path=header_path
            ))
        
        return chunks
    
    def _enhance_chunks(
        self,
        chunks: List[SemanticChunk]
    ) -> List[SemanticChunk]:
        """
        1. Skips sentence splitting for Code/Tables (Performance + Accuracy).
        2. Respects Section Boundaries (Prevents Hallucination).
        3. Filters Context by Type (Prevents Code polluting Text).
        """
        enhanced_chunks = []
        cfg = self.config.context
        total_chunks = len(chunks)
        
        # We don't want to split code or tables into "sentences"
        NATURAL_LANGUAGE_TYPES = {ElementType.PARAGRAPH.value, ElementType.LIST.value}

        # Instead of pre-calculating all, we store them only when needed/valid
        chunk_sentences_cache: Dict[int, List[str]] = {}

        def get_sentences(idx: int) -> List[str]:
            """Helper to safely get sentences for NL chunks only"""
            if idx not in chunk_sentences_cache:
                target_chunk = chunks[idx]
                if target_chunk.chunk_type in NATURAL_LANGUAGE_TYPES:
                    chunk_sentences_cache[idx] = self.sentence_splitter.split_sentences(
                        target_chunk.original_content
                    )
                else:
                    chunk_sentences_cache[idx] = [] # Empty for code/tables
            return chunk_sentences_cache[idx]

        needs_context = cfg.surrounding_sentences_before > 0 or cfg.surrounding_sentences_after > 0

        for i, chunk in enumerate(chunks):
            context = {}
            
            # Skip context injection for structured data (Tables/Code) 
            # if we only want to enrich text. 
            # (Optional: remove this if you want code to have text context, 
            # but usually you don't want Code to have "previous sentences" injected into its body)
            
            if needs_context:
                # --- Context BEFORE ---
                if cfg.surrounding_sentences_before > 0 and i > 0:
                    prev_sentences = []
                    # Look back up to 3 chunks
                    for j in range(i - 1, max(-1, i - 4), -1):
                        prev_chunk = chunks[j]
                        
                        # BOUNDARY CHECK: Stop if we hit a different top-level section
                        # This prevents "Chapter 1" context bleeding into "Chapter 2"
                        if prev_chunk.section_path != chunk.section_path:
                            # You might allow partial path matches, but strict is safer
                            break
                            
                        # TYPE CHECK: Don't pull "sentences" from a table/code block
                        if prev_chunk.chunk_type not in NATURAL_LANGUAGE_TYPES:
                            break
                            
                        sents = get_sentences(j)
                        prev_sentences = sents + prev_sentences
                        if len(prev_sentences) >= cfg.surrounding_sentences_before:
                            break
                    
                    if prev_sentences:
                        relevant = prev_sentences[-cfg.surrounding_sentences_before:]
                        context['before'] = ' '.join(relevant)
                
                # --- Context AFTER ---
                if cfg.surrounding_sentences_after > 0 and i < total_chunks - 1:
                    next_sentences = []
                    for j in range(i + 1, min(total_chunks, i + 4)):
                        next_chunk = chunks[j]
                        
                        # BOUNDARY CHECK
                        if next_chunk.section_path != chunk.section_path:
                            break
                            
                        # TYPE CHECK
                        if next_chunk.chunk_type not in NATURAL_LANGUAGE_TYPES:
                            break
                            
                        sents = get_sentences(j)
                        next_sentences.extend(sents)
                        if len(next_sentences) >= cfg.surrounding_sentences_after:
                            break
                    
                    if next_sentences:
                        relevant = next_sentences[:cfg.surrounding_sentences_after]
                        context['after'] = ' '.join(relevant)
            
            enriched = self.context_enricher.enrich_chunk(
                content=chunk.content,
                header_path=chunk.section_path,
                surrounding_context=context
            )
            
            chunk.content = enriched['content']
            chunk.token_count = self.token_counter.count_tokens(chunk.content)
            chunk.search_content = enriched.get('contextualized_content') or chunk.content
            
            enhanced_chunks.append(chunk)
        
        return enhanced_chunks
    
    def _is_metadata_noise(self, text: str) -> bool:
        """
        Heuristic: Detects Table of Contents, Bibliographies, and Header dumps.
        Returns True if the text is likely noise.
        """
        if not text or len(text) < 20:
            return False  # Too short to judge, keep it just in case
            
        words = text.split()
        if not words: return True
        
        # 1. Capitalization Check
        # Bibliographies often look like: "AUTHOR TITLE. AUTHOR TITLE."
        # If > 60% of words are Title Case or Uppercase, it's suspicious.
        cap_words = [w for w in words if w[0].isupper()]
        cap_ratio = len(cap_words) / len(words)
        
        if cap_ratio > 0.6:
            # 2. Verb Check (The safety valve)
            # Real content usually has common verbs (is, are, was, has, can, shows)
            common_verbs = {'is', 'are', 'was', 'were', 'has', 'have', 'can', 'will', 'shows', 'indicates'}
            # fast lowercase check
            has_verbs = any(v in text.lower().split() for v in common_verbs)
            
            if not has_verbs:
                logger.debug(f"Filtered noise chunk (Cap ratio: {cap_ratio:.2f}): {text[:50]}...")
                return True
                
        return False