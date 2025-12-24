"""Markdown parser - moved from parser.py"""
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class ElementType(Enum):
    """Types of markdown elements"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST = "list"
    TABLE = "table"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "horizontal_rule"


@dataclass
class MarkdownElement:
    """Represents a parsed markdown element"""
    type: ElementType
    content: str
    level: Optional[int] = None  # For headings (1-6)
    language: Optional[str] = None  # For code blocks
    metadata: Optional[dict] = None


class MarkdownParser:
    """Parse markdown content into structured elements"""
    
    def __init__(self):
        self.patterns = {
            'heading': re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
            'code_block': re.compile(r'^```(\w+)?\n(.*?)\n```$', re.MULTILINE | re.DOTALL),
            'horizontal_rule': re.compile(r'^(\*{3,}|-{3,}|_{3,})$', re.MULTILINE),
            'table': re.compile(r'^\|.+\|$', re.MULTILINE),
        }
    
    def parse(self, content: str) -> List[MarkdownElement]:
        """
        Parse markdown content into elements
        
        Args:
            content: Raw markdown text
            
        Returns:
            List of parsed markdown elements
        """
        if not content:
            return []
        
        elements = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                i += 1
                continue
            
            # Heading
            if line.startswith('#'):
                element, consumed = self._parse_heading(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue
            
            # Code block
            if line.startswith('```'):
                element, consumed = self._parse_code_block(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue
            
            # Table
            if '|' in line:
                element, consumed = self._parse_table(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue
            
            # List
            if self._is_list_item(line):
                element, consumed = self._parse_list(lines, i)
                if element:
                    elements.append(element)
                    i += consumed
                    continue
            
            # Horizontal rule
            if re.match(r'^[\*\-_]{3,}$', line.strip()):
                elements.append(MarkdownElement(
                    type=ElementType.HORIZONTAL_RULE,
                    content=line.strip()
                ))
                i += 1
                continue
            
            # Paragraph (default)
            element, consumed = self._parse_paragraph(lines, i)
            if element:
                elements.append(element)
                i += consumed
            else:
                i += 1
        
        logger.debug(f"Parsed {len(elements)} markdown elements")
        return elements
    
    def _parse_heading(self, lines: List[str], start: int) -> tuple[Optional[MarkdownElement], int]:
        """Parse heading element"""
        line = lines[start]
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        
        if not match:
            return None, 0
        
        level = len(match.group(1))
        content = match.group(2).strip()
        
        element = MarkdownElement(
            type=ElementType.HEADING,
            content=content,
            level=level
        )
        
        return element, 1
    
    def _parse_code_block(self, lines: List[str], start: int) -> tuple[Optional[MarkdownElement], int]:
        """Parse code block element"""
        if not lines[start].startswith('```'):
            return None, 0
        
        # Extract language if present
        first_line = lines[start]
        language = first_line[3:].strip() if len(first_line) > 3 else None
        
        # Find closing ```
        code_lines = []
        i = start + 1
        
        while i < len(lines):
            if lines[i].strip().startswith('```'):
                break
            code_lines.append(lines[i])
            i += 1
        
        if i >= len(lines):
            # No closing found, treat as paragraph
            return None, 0
        
        content = '\n'.join(code_lines)
        
        element = MarkdownElement(
            type=ElementType.CODE_BLOCK,
            content=content,
            language=language
        )
        
        consumed = i - start + 1
        return element, consumed
    
    def _parse_table(self, lines: List[str], start: int) -> tuple[Optional[MarkdownElement], int]:
        """Parse table element"""
        table_lines = []
        i = start
        
        while i < len(lines):
            line = lines[i].strip()
            if not line or '|' not in line:
                break
            table_lines.append(lines[i])
            i += 1
        
        if not table_lines:
            return None, 0
        
        content = '\n'.join(table_lines)
        
        element = MarkdownElement(
            type=ElementType.TABLE,
            content=content
        )
        
        consumed = len(table_lines)
        return element, consumed
    
    def _parse_list(self, lines: List[str], start: int) -> tuple[Optional[MarkdownElement], int]:
        """Parse list element"""
        list_lines = []
        i = start
        
        while i < len(lines):
            line = lines[i]
            
            # Empty line ends list
            if not line.strip():
                break
            
            # Check if it's a list item or continuation
            if self._is_list_item(line) or (list_lines and line.startswith('  ')):
                list_lines.append(line)
                i += 1
            else:
                break
        
        if not list_lines:
            return None, 0
        
        content = '\n'.join(list_lines)
        
        element = MarkdownElement(
            type=ElementType.LIST,
            content=content
        )
        
        consumed = len(list_lines)
        return element, consumed
    
    def _parse_paragraph(self, lines: List[str], start: int) -> tuple[Optional[MarkdownElement], int]:
        """Parse paragraph element"""
        para_lines = []
        i = start
        
        while i < len(lines):
            line = lines[i]
            
            # Empty line ends paragraph
            if not line.strip():
                break
            
            # Special markdown syntax ends paragraph
            if (line.startswith('#') or 
                line.startswith('```') or 
                '|' in line or 
                self._is_list_item(line) or
                re.match(r'^[\*\-_]{3,}$', line.strip())):
                break
            
            para_lines.append(line)
            i += 1
        
        if not para_lines:
            return None, 0
        
        content = '\n'.join(para_lines)
        
        element = MarkdownElement(
            type=ElementType.PARAGRAPH,
            content=content
        )
        
        consumed = len(para_lines)
        return element, consumed
    
    def _is_list_item(self, line: str) -> bool:
        """Check if line is a list item"""
        stripped = line.lstrip()
        
        # Unordered list
        if stripped.startswith(('- ', '* ', '+ ')):
            return True
        
        # Ordered list
        if re.match(r'^\d+\.\s', stripped):
            return True
        
        return False