"""
Optimized Markdown parser using markdown-it-py with O(N) single-pass processing.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import logging

from markdown_it import MarkdownIt
from markdown_it.token import Token

logger = logging.getLogger(__name__)

class ElementType(Enum):
    """Types of markdown elements"""
    DOCUMENT = "document"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "horizontal_rule"
    IMAGE = "image"
    TEXT = "text"

@dataclass
class MarkdownElement:
    """Represents a parsed markdown element with full context"""
    type: ElementType
    content: str
    level: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List['MarkdownElement'] = field(default_factory=list)
    
    def get_text_content(self) -> str:
        """Get all text content including children"""
        text_parts = [self.content] if self.content else []
        for child in self.children:
            text_parts.append(child.get_text_content())
        return '\n'.join(filter(None, text_parts))

class MarkdownParser:
    """Parse markdown using markdown-it-py (Optimized Single-Pass)"""
    
    def __init__(self):
        self.md = MarkdownIt("gfm-like", {"html": False})
        self.md.enable(['table', 'strikethrough'])
    
    def parse(self, content: str) -> List[MarkdownElement]:
        """
        Parse markdown content into structured elements
        """
        if not content:
            return []
            
        logger.info("Parsing markdown with markdown-it-py")
        tokens = self.md.parse(content)
        elements = self._tokens_to_elements(tokens, content)
        logger.info(f"Parsed {len(elements)} top-level elements")
        return elements
    
    def _tokens_to_elements(self, tokens: List[Token], content: str) -> List[MarkdownElement]:
        """Convert tokens to MarkdownElement objects using a single linear pass"""
        elements = []
        i = 0
        length = len(tokens)
        
        while i < length:
            token = tokens[i]
            
            # Skip closing tokens if encountered in the main loop (shouldn't happen often in well-formed structure)
            if token.nesting == -1:
                i += 1
                continue
                
            element = None
            next_index = i + 1
            
            # Dispatch based on token type
            if token.type == 'heading_open':
                element, next_index = self._process_heading(tokens, i)
            
            elif token.type == 'paragraph_open':
                element, next_index = self._process_paragraph(tokens, i)
            
            elif token.type in ('code_block', 'fence'):
                element = self._process_code_block(token)
                next_index = i + 1
            
            elif token.type == 'table_open':
                element, next_index = self._process_table(tokens, i, content)
            
            elif token.type in ('bullet_list_open', 'ordered_list_open'):
                element, next_index = self._process_list(tokens, i, content)
            
            elif token.type == 'blockquote_open':
                element, next_index = self._process_blockquote(tokens, i, content)
            
            elif token.type == 'hr':
                element = MarkdownElement(type=ElementType.HORIZONTAL_RULE, content='---')
                next_index = i + 1

            if element:
                elements.append(element)
                i = next_index
            else:
                i += 1
        
        return elements

    def _process_heading(self, tokens: List[Token], index: int) -> Tuple[MarkdownElement, int]:
        """Process heading (Structure: Open -> Inline -> Close)"""
        token = tokens[index]
        level = int(token.tag[1]) if len(token.tag) > 1 else 1
        
        # Guard against malformed tokens (e.g., end of stream)
        if index + 1 >= len(tokens):
            return MarkdownElement(ElementType.HEADING, "", level), index + 1

        inline_token = tokens[index + 1]
        text_content = self._extract_text_from_inline(inline_token)
        
        # Standard heading is 3 tokens. If structure varies, we could loop, but GFM is strict here.
        return MarkdownElement(
            type=ElementType.HEADING,
            content=text_content,
            level=level,
            metadata={'tag': token.tag}
        ), index + 3

    def _process_paragraph(self, tokens: List[Token], index: int) -> Tuple[MarkdownElement, int]:
        """Process paragraph (Structure: Open -> Inline -> Close)"""
        if index + 1 >= len(tokens):
            return MarkdownElement(ElementType.PARAGRAPH, ""), index + 1

        inline_token = tokens[index + 1]
        text_content = self._extract_text_from_inline(inline_token)
        
        has_image = any(child.type == 'image' for child in inline_token.children or [])
        
        return MarkdownElement(
            type=ElementType.PARAGRAPH,
            content=text_content,
            metadata={'has_image': has_image}
        ), index + 3

    def _process_code_block(self, token: Token) -> MarkdownElement:
        """Process code block (Atomic token)"""
        language = token.info.strip() if token.info else ''
        return MarkdownElement(
            type=ElementType.CODE_BLOCK,
            content=token.content.rstrip('\n'),
            metadata={
                'language': language,
                'is_fenced': token.type == 'fence'
            }
        )

    def _process_table(self, tokens: List[Token], start_index: int, content: str) -> Tuple[MarkdownElement, int]:
        """Process table by iterating tokens to count rows/cols"""
        rows = 0
        cols = 0
        current_idx = start_index + 1
        depth = 1
        start_token = tokens[start_index]
        
        while current_idx < len(tokens) and depth > 0:
            t = tokens[current_idx]
            
            # AST Metadata Extraction
            if t.type == 'tr_open':
                rows += 1
            elif rows == 1 and t.type == 'th_open':
                cols += 1
            
            # Nesting management
            if t.type == start_token.type:
                depth += 1
            elif t.type == start_token.type.replace('_open', '_close'):
                depth -= 1
            
            current_idx += 1
            
        table_content = self._extract_block_content(start_token, content)
        
        return MarkdownElement(
            type=ElementType.TABLE,
            content=table_content,
            metadata={
                'num_rows': rows,
                'num_cols': cols,
                'has_header': True
            }
        ), current_idx

    def _process_list(self, tokens: List[Token], start_index: int, content: str) -> Tuple[MarkdownElement, int]:
        """Process list by iterating tokens to count items"""
        item_count = 0
        current_idx = start_index + 1
        depth = 1
        start_token = tokens[start_index]
        is_ordered = start_token.type == 'ordered_list_open'
        
        while current_idx < len(tokens) and depth > 0:
            t = tokens[current_idx]
            
            # AST Metadata Extraction: Count items only at current level (depth 1)
            if t.type == 'list_item_open' and depth == 1:
                item_count += 1
            
            if t.type == start_token.type:
                depth += 1
            elif t.type == start_token.type.replace('_open', '_close'):
                depth -= 1
            
            current_idx += 1
            
        list_content = self._extract_block_content(start_token, content)
        
        return MarkdownElement(
            type=ElementType.LIST,
            content=list_content,
            metadata={
                'is_ordered': is_ordered,
                'item_count': item_count
            }
        ), current_idx

    def _process_blockquote(self, tokens: List[Token], start_index: int, content: str) -> Tuple[MarkdownElement, int]:
        """Process blockquote (Generic container processing)"""
        current_idx = start_index + 1
        depth = 1
        start_token = tokens[start_index]
        
        while current_idx < len(tokens) and depth > 0:
            t = tokens[current_idx]
            if t.type == start_token.type:
                depth += 1
            elif t.type == start_token.type.replace('_open', '_close'):
                depth -= 1
            current_idx += 1
            
        quote_content = self._extract_block_content(start_token, content)
        
        return MarkdownElement(
            type=ElementType.BLOCKQUOTE,
            content=quote_content
        ), current_idx

    def _extract_block_content(self, token: Token, content: str) -> str:
        """Extract raw text for a block using token map"""
        if not token.map:
            return ""
        
        line_start, line_end = token.map
        # splitlines(keepends=True) ensures we don't lose formatting structure
        lines = content.splitlines(keepends=True)
        
        # Safety check for bounds
        if line_start >= len(lines): 
            return ""
            
        return "".join(lines[line_start:line_end])

    def _extract_text_from_inline(self, inline_token: Token) -> str:
        """Extract text content from inline token"""
        if not inline_token or not inline_token.children:
            return inline_token.content if inline_token else ''
        
        text_parts = []
        for child in inline_token.children:
            if child.type in ('text', 'code_inline'):
                text_parts.append(child.content)
            elif child.type in ('softbreak', 'hardbreak'):
                text_parts.append('\n')
        
        return ''.join(text_parts)

    def get_header_hierarchy(self, elements: List[MarkdownElement]) -> Dict[int, List[str]]:
        """Build header hierarchy mapping"""
        hierarchy = {}
        current_headers = {}
        
        for idx, element in enumerate(elements):
            if element.type == ElementType.HEADING:
                level = element.level
                current_headers[level] = element.content
                # Clear deeper levels
                current_headers = {k: v for k, v in current_headers.items() if k <= level}
            
            path = [current_headers[lvl] for lvl in sorted(current_headers.keys())]
            hierarchy[idx] = path
        
        return hierarchy