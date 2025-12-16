from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum
import re


class ElementType(Enum):
    """Types of markdown elements"""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    CODE_BLOCK = "code_block"
    IMAGE = "image"
    HORIZONTAL_RULE = "horizontal_rule"


@dataclass
class MarkdownElement:
    """Represents a parsed markdown element"""
    type: ElementType
    content: str
    level: Optional[int] = None  # For headers
    line_start: int = 0
    line_end: int = 0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MarkdownParser:
    """Parse markdown content into structured elements"""
    
    def __init__(self):
        self.header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        self.table_separator = re.compile(r'^\|?[\s\-:|]+\|?$')
        self.list_pattern = re.compile(r'^(\s*)([\*\-\+]|\d+\.)\s+(.+)$')
        self.code_fence = re.compile(r'^```(\w*)$')
        self.image_pattern = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')
        self.hr_pattern = re.compile(r'^(\*\*\*|---|___)$')
    
    def parse(self, content: str) -> List[MarkdownElement]:
        """Parse markdown content into elements"""
        lines = content.split('\n')
        elements = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if header := self.header_pattern.match(line):
                level = len(header.group(1))
                text = header.group(2)
                elements.append(MarkdownElement(
                    type=ElementType.HEADER,
                    content=text,
                    level=level,
                    line_start=i,
                    line_end=i
                ))
                i += 1
                continue
            
            if self.hr_pattern.match(line.strip()):
                elements.append(MarkdownElement(
                    type=ElementType.HORIZONTAL_RULE,
                    content=line,
                    line_start=i,
                    line_end=i
                ))
                i += 1
                continue
            
            if code_match := self.code_fence.match(line.strip()):
                lang = code_match.group(1)
                start = i
                i += 1
                code_lines = []
                while i < len(lines) and not self.code_fence.match(lines[i].strip()):
                    code_lines.append(lines[i])
                    i += 1
                elements.append(MarkdownElement(
                    type=ElementType.CODE_BLOCK,
                    content='\n'.join(code_lines),
                    line_start=start,
                    line_end=i,
                    metadata={'language': lang}
                ))
                i += 1
                continue
            
            if '|' in line and i + 1 < len(lines):
                if self.table_separator.match(lines[i + 1].strip()):
                    table_lines, end = self._parse_table(lines, i)
                    elements.append(MarkdownElement(
                        type=ElementType.TABLE,
                        content='\n'.join(table_lines),
                        line_start=i,
                        line_end=end,
                        metadata=self._parse_table_metadata(table_lines)
                    ))
                    i = end + 1
                    continue
            
            if self.list_pattern.match(line):
                list_lines, end = self._parse_list(lines, i)
                elements.append(MarkdownElement(
                    type=ElementType.LIST,
                    content='\n'.join(list_lines),
                    line_start=i,
                    line_end=end,
                    metadata={'item_count': len(list_lines)}
                ))
                i = end + 1
                continue
            
            if self.image_pattern.search(line):
                elements.append(MarkdownElement(
                    type=ElementType.IMAGE,
                    content=line,
                    line_start=i,
                    line_end=i,
                    metadata=self._parse_image_metadata(line)
                ))
                i += 1
                continue
            
            if line.strip():
                para_lines, end = self._parse_paragraph(lines, i)
                elements.append(MarkdownElement(
                    type=ElementType.PARAGRAPH,
                    content='\n'.join(para_lines),
                    line_start=i,
                    line_end=end
                ))
                i = end + 1
                continue
            
            i += 1
        
        return elements
    
    def _parse_table(self, lines: List[str], start: int) -> Tuple[List[str], int]:
        """Parse a table starting at given line"""
        table_lines = [lines[start], lines[start + 1]]
        i = start + 2
        
        while i < len(lines) and '|' in lines[i] and lines[i].strip():
            table_lines.append(lines[i])
            i += 1
        
        return table_lines, i - 1
    
    def _parse_table_metadata(self, table_lines: List[str]) -> dict:
        """Extract metadata from table"""
        header = table_lines[0]
        num_cols = header.count('|') - 1 if header.startswith('|') else header.count('|') + 1
        num_rows = len(table_lines) - 2  # Exclude header and separator
        
        return {
            'num_cols': num_cols,
            'num_rows': num_rows,
            'has_header': True
        }
    
    def _parse_list(self, lines: List[str], start: int) -> Tuple[List[str], int]:
        """Parse a list starting at given line"""
        list_lines = [lines[start]]
        i = start + 1
        
        while i < len(lines):
            line = lines[i]
            # Continue if it's a list item or indented continuation
            if self.list_pattern.match(line) or (line.startswith('  ') and line.strip()):
                list_lines.append(line)
                i += 1
            elif not line.strip():
                # Empty line might separate list items, check next
                if i + 1 < len(lines) and self.list_pattern.match(lines[i + 1]):
                    list_lines.append(line)
                    i += 1
                else:
                    break
            else:
                break
        
        return list_lines, i - 1
    
    def _parse_paragraph(self, lines: List[str], start: int) -> Tuple[List[str], int]:
        """Parse a paragraph starting at given line"""
        para_lines = [lines[start]]
        i = start + 1
        
        while i < len(lines):
            line = lines[i]
            # Stop at empty line, header, list, table, or code block
            if (not line.strip() or 
                self.header_pattern.match(line) or
                self.list_pattern.match(line) or
                '|' in line or
                self.code_fence.match(line.strip()) or
                self.hr_pattern.match(line.strip())):
                break
            para_lines.append(line)
            i += 1
        
        return para_lines, i - 1
    
    def _parse_image_metadata(self, line: str) -> dict:
        """Extract image metadata"""
        match = self.image_pattern.search(line)
        if match:
            return {
                'caption': match.group(1),
                'path': match.group(2)
            }
        return {}
    
    def get_header_path(self, elements: List[MarkdownElement], index: int) -> List[str]:
        """Get hierarchical path of headers leading to element at index"""
        path = []
        current_levels = {}
        
        for i in range(index + 1):
            elem = elements[i]
            if elem.type == ElementType.HEADER:
                level = elem.level
                current_levels[level] = elem.content
                # Clear deeper levels
                current_levels = {k: v for k, v in current_levels.items() if k <= level}
        
        # Build path from level 1 to deepest
        for level in sorted(current_levels.keys()):
            path.append(current_levels[level])
        
        return path