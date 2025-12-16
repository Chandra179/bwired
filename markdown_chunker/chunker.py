"""
Core chunking logic with content-type specific rules
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging

from .parser import MarkdownElement, ElementType, MarkdownParser
from .tokenizer_utils import TokenCounter
from .config import EmbeddingConfig

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a chunk of content ready for embedding"""
    content: str
    token_count: int
    chunk_type: str
    metadata: Dict[str, Any]
    element_index: int
    chunk_index: int = 0
    total_chunks: int = 1


class MarkdownChunker:
    """Chunk markdown content based on token limits and content type"""
    
    def __init__(self, config: EmbeddingConfig, token_counter: TokenCounter):
        self.config = config
        self.token_counter = token_counter
        self.parser = MarkdownParser()
    
    def chunk_document(self, content: str, document_id: str, document_title: str = "") -> List[Chunk]:
        """
        Chunk entire markdown document
        
        Args:
            content: Markdown content
            document_id: Unique document identifier
            document_title: Optional document title
            
        Returns:
            List of chunks
        """
        logger.info(f"Parsing document: {document_id}")
        elements = self.parser.parse(content)
        logger.info(f"Found {len(elements)} markdown elements")
        
        all_chunks = []
        previous_chunk_content = ""
        
        for idx, element in enumerate(elements):
            header_path = self.parser.get_header_path(elements, idx)
            
            # Get context from surrounding elements
            context = self._get_element_context(elements, idx)
            
            # Chunk based on element type
            chunks = self._chunk_element(element, idx, context, header_path, document_id, document_title)
            
            # Add overlap from previous chunk
            if all_chunks and self.config.overlap_tokens > 0 and chunks:
                overlap = self.token_counter.get_overlap_text(
                    previous_chunk_content, 
                    self.config.overlap_tokens,
                    from_start=False
                )
                if overlap:
                    chunks[0].content = f"{overlap}\n\n{chunks[0].content}"
                    chunks[0].token_count = self.token_counter.count_tokens(chunks[0].content)
                    chunks[0].metadata['has_overlap'] = True
            
            all_chunks.extend(chunks)
            
            if chunks:
                previous_chunk_content = chunks[-1].content
        
        logger.info(f"Generated {len(all_chunks)} total chunks")
        return all_chunks
    
    def _chunk_element(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Chunk a single element based on its type"""
        
        if element.type == ElementType.TABLE:
            return self._chunk_table(element, element_index, context, header_path, document_id, document_title)
        elif element.type == ElementType.LIST:
            return self._chunk_list(element, element_index, context, header_path, document_id, document_title)
        elif element.type == ElementType.PARAGRAPH:
            return self._chunk_text(element, element_index, context, header_path, document_id, document_title)
        elif element.type == ElementType.CODE_BLOCK:
            return self._chunk_code(element, element_index, context, header_path, document_id, document_title)
        elif element.type == ElementType.HEADER:
            return self._chunk_header(element, element_index, header_path, document_id, document_title)
        elif element.type == ElementType.IMAGE:
            return self._chunk_image(element, element_index, context, header_path, document_id, document_title)
        else:
            # Default: treat as text
            return self._chunk_text(element, element_index, context, header_path, document_id, document_title)
    
    def _chunk_table(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Chunk a table"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # If table fits in one chunk, keep it intact
        if token_count <= self.config.target_chunk_size:
            content_with_context = self._add_context_to_content(element.content, context, header_path)
            final_token_count = self.token_counter.count_tokens(content_with_context)
            
            return [Chunk(
                content=content_with_context,
                token_count=final_token_count,
                chunk_type="table",
                metadata=self._build_metadata(
                    document_id, document_title, element, header_path, 
                    {"table_complete": True, **element.metadata}
                ),
                element_index=element_index,
                chunk_index=0,
                total_chunks=1
            )]
        
        # Table is too large, split by rows
        return self._split_table_by_rows(
            element, element_index, context, header_path, document_id, document_title
        )
    
    def _split_table_by_rows(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str,
        recursion_depth: int = 0
    ) -> List[Chunk]:
        """Split table by rows"""
        lines = element.content.split('\n')
        header_row = lines[0]
        separator = lines[1]
        data_rows = lines[2:]
        
        if not data_rows:
            # No data rows, return header only
            content_with_context = self._add_context_to_content(element.content, context, header_path)
            return [Chunk(
                content=content_with_context,
                token_count=self.token_counter.count_tokens(content_with_context),
                chunk_type="table",
                metadata=self._build_metadata(document_id, document_title, element, header_path, element.metadata),
                element_index=element_index
            )]
        
        # Calculate rows per chunk
        header_tokens = self.token_counter.count_tokens(header_row + '\n' + separator)
        avg_row_tokens = sum(self.token_counter.count_tokens(row) for row in data_rows) / len(data_rows)
        
        available_tokens = self.config.target_chunk_size - header_tokens - 50  # Buffer for context
        rows_per_chunk = max(1, int(available_tokens / avg_row_tokens))
        
        chunks = []
        for i in range(0, len(data_rows), rows_per_chunk):
            chunk_rows = data_rows[i:i + rows_per_chunk]
            table_chunk = '\n'.join([header_row, separator] + chunk_rows)
            
            content_with_context = self._add_context_to_content(table_chunk, context, header_path)
            token_count = self.token_counter.count_tokens(content_with_context)
            
            # Check if still too large
            if token_count > self.config.max_token_limit and recursion_depth < self.config.max_recursion_depth:
                # Further split needed
                logger.warning(f"Table chunk still too large ({token_count} tokens), further splitting...")
                if rows_per_chunk > 1:
                    # Try with fewer rows
                    rows_per_chunk = rows_per_chunk // 2
                    continue
            
            chunk_metadata = self._build_metadata(
                document_id, document_title, element, header_path,
                {
                    "table_chunk": True,
                    "row_range": f"{i}-{i + len(chunk_rows)} of {len(data_rows)}",
                    **element.metadata
                }
            )
            
            chunks.append(Chunk(
                content=self._truncate_if_needed(content_with_context, token_count),
                token_count=min(token_count, self.config.max_token_limit),
                chunk_type="table",
                metadata=chunk_metadata,
                element_index=element_index,
                chunk_index=len(chunks),
                total_chunks=0  # Will update after
            ))
        
        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _chunk_list(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Chunk a list"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # If list fits in one chunk, keep it intact
        if token_count <= self.config.target_chunk_size:
            content_with_context = self._add_context_to_content(element.content, context, header_path)
            final_token_count = self.token_counter.count_tokens(content_with_context)
            
            return [Chunk(
                content=content_with_context,
                token_count=final_token_count,
                chunk_type="list",
                metadata=self._build_metadata(
                    document_id, document_title, element, header_path,
                    {"list_complete": True, **element.metadata}
                ),
                element_index=element_index
            )]
        
        # Split by items
        return self._split_list_by_items(
            element, element_index, context, header_path, document_id, document_title
        )
    
    def _split_list_by_items(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Split list by items"""
        items = element.content.split('\n')
        items = [item for item in items if item.strip()]
        
        chunks = []
        current_items = []
        current_tokens = 0
        
        for item in items:
            item_tokens = self.token_counter.count_tokens(item)
            
            if current_tokens + item_tokens <= self.config.target_chunk_size:
                current_items.append(item)
                current_tokens += item_tokens
            else:
                if current_items:
                    chunk_content = '\n'.join(current_items)
                    content_with_context = self._add_context_to_content(chunk_content, context, header_path)
                    
                    chunks.append(Chunk(
                        content=content_with_context,
                        token_count=self.token_counter.count_tokens(content_with_context),
                        chunk_type="list",
                        metadata=self._build_metadata(
                            document_id, document_title, element, header_path,
                            {"list_chunk": True, "item_count": len(current_items)}
                        ),
                        element_index=element_index,
                        chunk_index=len(chunks)
                    ))
                
                current_items = [item]
                current_tokens = item_tokens
        
        if current_items:
            chunk_content = '\n'.join(current_items)
            content_with_context = self._add_context_to_content(chunk_content, context, header_path)
            
            chunks.append(Chunk(
                content=content_with_context,
                token_count=self.token_counter.count_tokens(content_with_context),
                chunk_type="list",
                metadata=self._build_metadata(
                    document_id, document_title, element, header_path,
                    {"list_chunk": True, "item_count": len(current_items)}
                ),
                element_index=element_index,
                chunk_index=len(chunks)
            ))
        
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _chunk_text(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Chunk text/paragraph"""
        token_count = self.token_counter.count_tokens(element.content)
        
        if token_count <= self.config.target_chunk_size:
            return [Chunk(
                content=element.content,
                token_count=token_count,
                chunk_type=element.type.value,
                metadata=self._build_metadata(document_id, document_title, element, header_path),
                element_index=element_index
            )]
        
        # Split text by tokens
        text_chunks = self.token_counter.split_by_tokens(element.content, self.config.target_chunk_size)
        
        chunks = []
        for i, text_chunk in enumerate(text_chunks):
            token_count = self.token_counter.count_tokens(text_chunk)
            
            chunks.append(Chunk(
                content=self._truncate_if_needed(text_chunk, token_count),
                token_count=min(token_count, self.config.max_token_limit),
                chunk_type=element.type.value,
                metadata=self._build_metadata(document_id, document_title, element, header_path),
                element_index=element_index,
                chunk_index=i,
                total_chunks=len(text_chunks)
            ))
        
        return chunks
    
    def _chunk_code(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Chunk code block"""
        # Similar to text, but preserve code structure
        return self._chunk_text(element, element_index, context, header_path, document_id, document_title)
    
    def _chunk_header(
        self, 
        element: MarkdownElement, 
        element_index: int,
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Chunk header (usually merged with next section)"""
        token_count = self.token_counter.count_tokens(element.content)
        
        # If header is very short or empty, it will be merged with next section
        if token_count < self.config.min_chunk_size:
            return []
        
        return [Chunk(
            content=element.content,
            token_count=token_count,
            chunk_type="header",
            metadata=self._build_metadata(
                document_id, document_title, element, header_path,
                {"header_level": element.level}
            ),
            element_index=element_index
        )]
    
    def _chunk_image(
        self, 
        element: MarkdownElement, 
        element_index: int,
        context: Dict[str, str],
        header_path: List[str],
        document_id: str,
        document_title: str
    ) -> List[Chunk]:
        """Chunk image with surrounding context"""
        # Include image caption with context
        content_with_context = self._add_context_to_content(element.content, context, header_path)
        token_count = self.token_counter.count_tokens(content_with_context)
        
        return [Chunk(
            content=content_with_context,
            token_count=token_count,
            chunk_type="image",
            metadata=self._build_metadata(
                document_id, document_title, element, header_path,
                {"image_metadata": element.metadata}
            ),
            element_index=element_index
        )]
    
    def _get_element_context(self, elements: List[MarkdownElement], index: int) -> Dict[str, str]:
        """Get context from surrounding elements"""
        context = {}
        
        # Previous paragraph/text
        if index > 0:
            prev = elements[index - 1]
            if prev.type in [ElementType.PARAGRAPH, ElementType.HEADER]:
                context['before'] = prev.content[:200]  # First 200 chars
        
        # Next paragraph/text
        if index < len(elements) - 1:
            next_elem = elements[index + 1]
            if next_elem.type == ElementType.PARAGRAPH:
                context['after'] = next_elem.content[:200]
        
        return context
    
    def _add_context_to_content(self, content: str, context: Dict[str, str], header_path: List[str]) -> str:
        """Add contextual information to content"""
        parts = []
        
        # Add header path
        if header_path:
            parts.append(f"Context: {' > '.join(header_path)}\n")
        
        # Add before context
        if 'before' in context:
            parts.append(f"[Previous context: {context['before']}]\n")
        
        # Main content
        parts.append(content)
        
        # Add after context
        if 'after' in context:
            parts.append(f"\n[Following context: {context['after']}]")
        
        return '\n'.join(parts)
    
    def _build_metadata(
        self, 
        document_id: str, 
        document_title: str, 
        element: MarkdownElement,
        header_path: List[str],
        extra: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Build metadata dictionary"""
        metadata = {
            "document_id": document_id,
            "document_title": document_title,
            "chunk_type": element.type.value,
            "header_path": header_path,
            "line_start": element.line_start,
            "line_end": element.line_end
        }
        
        if extra:
            metadata.update(extra)
        
        return metadata
    
    def _truncate_if_needed(self, content: str, token_count: int) -> str:
        """Truncate content if exceeds max token limit"""
        if token_count <= self.config.max_token_limit:
            return content
        
        logger.warning(f"Truncating content from {token_count} to {self.config.max_token_limit} tokens")
        
        # Simple truncation by words
        words = content.split()
        truncated = ""
        for word in words:
            test = truncated + " " + word if truncated else word
            if self.token_counter.count_tokens(test) >= self.config.max_token_limit - self.config.truncation_buffer:
                break
            truncated = test
        
        return truncated + "... [truncated]"