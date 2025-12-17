"""
Markdown parser using markdown-it-py for robust AST generation
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
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
    level: Optional[int] = None  # For headings (1-6)
    line_start: int = 0
    line_end: int = 0
    metadata: Dict[str, Any] = None
    children: List['MarkdownElement'] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.children is None:
            self.children = []
    
    def get_text_content(self) -> str:
        """Get all text content including children"""
        text_parts = [self.content] if self.content else []
        for child in self.children:
            text_parts.append(child.get_text_content())
        return '\n'.join(filter(None, text_parts))


class MarkdownParser:
    """Parse markdown using markdown-it-py"""
    
    def __init__(self):
        # Initialize with GFM (GitHub Flavored Markdown) support
        self.md = MarkdownIt("gfm-like", {"html": False})
        self.md.enable(['table', 'strikethrough'])
    
    def parse(self, content: str) -> List[MarkdownElement]:
        """
        Parse markdown content into structured elements
        
        Args:
            content: Markdown text
            
        Returns:
            List of top-level MarkdownElement objects
        """
        logger.info("Parsing markdown with markdown-it-py")
        
        tokens = self.md.parse(content)
        elements = self._tokens_to_elements(tokens, content)
        
        logger.info(f"Parsed {len(elements)} top-level elements")
        return elements
    
    def _tokens_to_elements(self, tokens: List[Token], content: str) -> List[MarkdownElement]:
        """Convert tokens to MarkdownElement objects"""
        elements = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            # Skip closing tokens
            if token.nesting == -1:
                i += 1
                continue
            
            element = self._process_token(token, tokens, i, content)
            if element:
                elements.append(element)
                # Skip to the matching closing token if block
                if token.nesting == 1:
                    i = self._find_closing_token(tokens, i) + 1
                else:
                    i += 1
            else:
                i += 1
        
        return elements
    
    def _process_token(
        self, 
        token: Token, 
        tokens: List[Token], 
        index: int,
        content: str
    ) -> Optional[MarkdownElement]:
        """Process a single token into MarkdownElement"""
        
        if token.type == 'heading_open':
            return self._process_heading(token, tokens, index, content)
        
        elif token.type == 'paragraph_open':
            return self._process_paragraph(token, tokens, index, content)
        
        elif token.type == 'code_block' or token.type == 'fence':
            return self._process_code_block(token, content)
        
        elif token.type == 'table_open':
            return self._process_table(token, tokens, index, content)
        
        elif token.type == 'bullet_list_open' or token.type == 'ordered_list_open':
            return self._process_list(token, tokens, index, content)
        
        elif token.type == 'blockquote_open':
            return self._process_blockquote(token, tokens, index, content)
        
        elif token.type == 'hr':
            return self._process_hr(token)
        
        return None
    
    def _process_heading(
        self, 
        token: Token, 
        tokens: List[Token], 
        index: int,
        content: str
    ) -> MarkdownElement:
        """Process heading"""
        # Extract level from tag (h1, h2, etc.)
        level = int(token.tag[1])
        
        # Get content from inline token
        inline_token = tokens[index + 1]
        text_content = self._extract_text_from_inline(inline_token)
        
        return MarkdownElement(
            type=ElementType.HEADING,
            content=text_content,
            level=level,
            line_start=token.map[0] if token.map else 0,
            line_end=token.map[1] if token.map else 0,
            metadata={'tag': token.tag}
        )
    
    def _process_paragraph(
        self, 
        token: Token, 
        tokens: List[Token], 
        index: int,
        content: str
    ) -> MarkdownElement:
        """Process paragraph"""
        # Get content from inline token
        inline_token = tokens[index + 1]
        text_content = self._extract_text_from_inline(inline_token)
        
        # Check for images in the inline content
        has_image = any(child.type == 'image' for child in inline_token.children or [])
        
        return MarkdownElement(
            type=ElementType.PARAGRAPH,
            content=text_content,
            line_start=token.map[0] if token.map else 0,
            line_end=token.map[1] if token.map else 0,
            metadata={'has_image': has_image}
        )
    
    def _process_code_block(self, token: Token, content: str) -> MarkdownElement:
        """Process code block"""
        language = token.info.strip() if token.info else ''
        
        return MarkdownElement(
            type=ElementType.CODE_BLOCK,
            content=token.content.rstrip('\n'),
            line_start=token.map[0] if token.map else 0,
            line_end=token.map[1] if token.map else 0,
            metadata={
                'language': language,
                'is_fenced': token.type == 'fence'
            }
        )
    
    def _process_table(
        self, 
        token: Token, 
        tokens: List[Token], 
        index: int,
        content: str
    ) -> MarkdownElement:
        """Process table"""
        # Extract table content from source
        line_start = token.map[0] if token.map else 0
        line_end = self._find_closing_token_map(tokens, index)
        
        lines = content.split('\n')
        table_content = '\n'.join(lines[line_start:line_end])
        
        # Count rows and columns
        table_lines = [l for l in table_content.split('\n') if l.strip()]
        num_rows = len(table_lines) - 2 if len(table_lines) > 2 else 0  # Exclude header and separator
        num_cols = table_lines[0].count('|') - 1 if table_lines and '|' in table_lines[0] else 0
        
        return MarkdownElement(
            type=ElementType.TABLE,
            content=table_content,
            line_start=line_start,
            line_end=line_end,
            metadata={
                'num_rows': num_rows,
                'num_cols': num_cols,
                'has_header': True
            }
        )
    
    def _process_list(
        self, 
        token: Token, 
        tokens: List[Token], 
        index: int,
        content: str
    ) -> MarkdownElement:
        """Process list (ordered or unordered)"""
        is_ordered = token.type == 'ordered_list_open'
        
        # Extract list content
        line_start = token.map[0] if token.map else 0
        line_end = self._find_closing_token_map(tokens, index)
        
        lines = content.split('\n')
        list_content = '\n'.join(lines[line_start:line_end])
        
        # Count items (simple approximation)
        item_count = list_content.count('\n- ') + list_content.count('\n* ') + \
                     list_content.count('\n+ ') + list_content.count('\n1. ')
        if list_content.strip().startswith(('-', '*', '+', '1.')):
            item_count += 1
        
        return MarkdownElement(
            type=ElementType.LIST,
            content=list_content,
            line_start=line_start,
            line_end=line_end,
            metadata={
                'is_ordered': is_ordered,
                'item_count': item_count
            }
        )
    
    def _process_blockquote(
        self, 
        token: Token, 
        tokens: List[Token], 
        index: int,
        content: str
    ) -> MarkdownElement:
        """Process blockquote"""
        line_start = token.map[0] if token.map else 0
        line_end = self._find_closing_token_map(tokens, index)
        
        lines = content.split('\n')
        quote_content = '\n'.join(lines[line_start:line_end])
        
        return MarkdownElement(
            type=ElementType.BLOCKQUOTE,
            content=quote_content,
            line_start=line_start,
            line_end=line_end
        )
    
    def _process_hr(self, token: Token) -> MarkdownElement:
        """Process horizontal rule"""
        return MarkdownElement(
            type=ElementType.HORIZONTAL_RULE,
            content='---',
            line_start=token.map[0] if token.map else 0,
            line_end=token.map[1] if token.map else 0
        )
    
    def _extract_text_from_inline(self, inline_token: Token) -> str:
        """Extract text content from inline token"""
        if not inline_token or not inline_token.children:
            return inline_token.content if inline_token else ''
        
        text_parts = []
        for child in inline_token.children:
            if child.type == 'text' or child.type == 'code_inline':
                text_parts.append(child.content)
            elif child.type == 'softbreak' or child.type == 'hardbreak':
                text_parts.append('\n')
        
        return ''.join(text_parts)
    
    def _find_closing_token(self, tokens: List[Token], start_index: int) -> int:
        """Find the index of matching closing token"""
        open_token = tokens[start_index]
        depth = 1
        
        for i in range(start_index + 1, len(tokens)):
            if tokens[i].type == open_token.type:
                depth += 1
            elif tokens[i].type == open_token.type.replace('_open', '_close'):
                depth -= 1
                if depth == 0:
                    return i
        
        return start_index
    
    def _find_closing_token_map(self, tokens: List[Token], start_index: int) -> int:
        """Find the line_end from closing token's map"""
        closing_index = self._find_closing_token(tokens, start_index)
        if closing_index < len(tokens) and tokens[closing_index].map:
            return tokens[closing_index].map[1]
        return tokens[start_index].map[1] if tokens[start_index].map else 0
    
    def get_header_hierarchy(self, elements: List[MarkdownElement]) -> Dict[int, List[str]]:
        """
        Build header hierarchy mapping
        
        Returns:
            Dict mapping element index to header path
        """
        hierarchy = {}
        current_headers = {}  # level -> header text
        
        for idx, element in enumerate(elements):
            if element.type == ElementType.HEADING:
                level = element.level
                current_headers[level] = element.content
                # Clear deeper levels
                current_headers = {k: v for k, v in current_headers.items() if k <= level}
            
            # Build path for current element
            path = []
            for level in sorted(current_headers.keys()):
                path.append(current_headers[level])
            hierarchy[idx] = path
        
        return hierarchy