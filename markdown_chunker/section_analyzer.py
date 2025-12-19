"""
Semantic section extraction from parsed markdown elements
"""
from dataclasses import dataclass
from typing import List, Optional
import logging

from .parser import MarkdownElement, ElementType

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Represents a semantic section of the document"""
    heading: Optional[MarkdownElement]
    content_elements: List[MarkdownElement]
    level: int  # Heading level (0 for root, 1-6 for h1-h6)
    subsections: List['Section']
    start_index: int  # Index in original elements list
    end_index: int    # Index in original elements list


class SectionAnalyzer:
    """Extract semantic sections from markdown elements"""
    
    def __init__(self):
        self.sections = []
    
    def analyze(self, elements: List[MarkdownElement]) -> List[Section]:
        """
        Extract hierarchical sections from flat element list
        
        Args:
            elements: Flat list of parsed markdown elements
            
        Returns:
            List of top-level sections with nested subsections
        """
        logger.info(f"Analyzing {len(elements)} elements for semantic sections")
        
        if not elements:
            return []
        
        sections = self._build_hierarchy(elements)
        
        logger.info(f"Extracted {len(sections)} top-level sections")
        return sections
    
    def _build_hierarchy(self, elements: List[MarkdownElement]) -> List[Section]:
        """Build hierarchical section structure, ignoring content before first header"""
        if not elements:
            return []
        
        sections = []
        i = 0
        
        # Skip any content before the first heading
        while i < len(elements) and elements[i].type != ElementType.HEADING:
            logger.debug(f"Skipping element at index {i} before first header")
            i += 1
        
        # Process sections starting from first heading
        while i < len(elements):
            element = elements[i]
            
            if element.type == ElementType.HEADING: 
                # Start new section
                section, next_index = self._extract_section(elements, i)
                sections.append(section)
                i = next_index
            else:
                # This shouldn't happen if logic is correct, but skip just in case
                i += 1
        
        return sections
    
    def _extract_section(
        self, 
        elements: List[MarkdownElement], 
        start_index: int
    ) -> tuple[Section, int]:
        """
        Extract a section starting at given index
        
        Returns:
            (Section object, next_index to process)
        """
        heading = elements[start_index]
        level = heading.level
        content_start = start_index + 1
        
        content_elements = []
        subsections = []
        current_index = content_start
        
        # Collect content until next same-or-higher level heading
        while current_index < len(elements):
            elem = elements[current_index]
            
            if elem.type == ElementType.HEADING:
                if elem.level <= level: # could be open and close tag so we need to check the level
                    # Next section at same or higher level
                    break
                else:
                    # Subsection - extract recursively
                    subsection, next_index = self._extract_section(elements, current_index)
                    subsections.append(subsection)
                    current_index = next_index
            else:
                # Regular content element
                content_elements.append(elem)
                current_index += 1
        
        section = Section(
            heading=heading,
            content_elements=content_elements,
            level=level,
            subsections=subsections,
            start_index=start_index,
            end_index=current_index - 1
        )
        
        return section, current_index