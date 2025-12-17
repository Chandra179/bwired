from typing import Dict, Any, List, Optional
import logging

from .parser import MarkdownElement
from .config import ContextConfig

logger = logging.getLogger(__name__)


try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class ContextEnricher:
    """Enhance chunks with context for better RAG retrieval"""
    
    def __init__(self, config: ContextConfig):
        self.config = config
        self.nlp = None
        
        # Load spaCy for entity extraction if needed
        if config.extract_entities and SPACY_AVAILABLE:
            try:
                logger.info("Loading spaCy for entity extraction")
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy loaded for entity extraction")
            except OSError:
                logger.warning("spaCy model not available, entity extraction disabled")
    
    def enrich_chunk(
        self,
        content: str,
        chunk_type: str,
        header_path: List[str],
        document_title: str,
        element: Optional[MarkdownElement] = None,
        surrounding_context: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Enrich a chunk with contextual information
        
        Args:
            content: Chunk content
            chunk_type: Type of chunk (table, code, paragraph, etc.)
            header_path: Hierarchical path of headers
            document_title: Document title
            element: Original MarkdownElement (for metadata)
            surrounding_context: Optional surrounding text
            
        Returns:
            Dict with enriched content and metadata
        """
        enriched = {
            'content': content,
            'original_content': content,  # Keep original
            'metadata': {}
        }
        
        # Add document context
        if self.config.include_document_context:
            enriched['metadata']['document_title'] = document_title
        
        # Add header path
        if self.config.include_header_path and header_path:
            enriched['metadata']['header_path'] = header_path
            enriched['metadata']['section_context'] = ' > '.join(header_path)
        
        # Add surrounding context
        if self.config.include_surrounding_context and surrounding_context:
            context_parts = []
            
            if 'before' in surrounding_context:
                context_parts.append(f"[Context before: {surrounding_context['before']}]")
            
            context_parts.append(content)
            
            if 'after' in surrounding_context:
                context_parts.append(f"[Context after: {surrounding_context['after']}]")
            
            enriched['content'] = '\n'.join(context_parts)
        
        # Extract entities
        if self.config.extract_entities:
            entities = self._extract_entities(content)
            if entities:
                enriched['metadata']['entities'] = entities
        
        # Multi-representation for special types
        if chunk_type == 'table' and self.config.create_table_descriptions:
            table_desc = self._create_table_description(content, element)
            enriched['metadata']['table_description'] = table_desc
            enriched['representations'] = {
                'natural_language': table_desc,
                'structured': content
            }
        
        elif chunk_type == 'code_block' and self.config.create_code_descriptions:
            code_desc = self._create_code_description(content, element)
            enriched['metadata']['code_description'] = code_desc
            enriched['representations'] = {
                'natural_language': code_desc,
                'code': content
            }
        
        return enriched
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text"""
        if not self.nlp or not text:
            return {}
        
        try:
            doc = self.nlp(text[:5000])  # Limit length for performance
            
            entities = {}
            for ent in doc.ents:
                if ent.label_ in self.config.entity_types:
                    if ent.label_ not in entities:
                        entities[ent.label_] = []
                    if ent.text not in entities[ent.label_]:
                        entities[ent.label_].append(ent.text)
            
            return entities
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return {}
    
    def _create_table_description(
        self, 
        table_content: str, 
        element: Optional[MarkdownElement]
    ) -> str:
        """
        Create natural language description of table
        Simple rule-based for now, can be enhanced with LLM later
        """
        lines = [l.strip() for l in table_content.split('\n') if l.strip() and '|' in l]
        
        if len(lines) < 2:
            return "Empty table"
        
        # Extract header
        header_line = lines[0]
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        
        # Count rows (excluding header and separator)
        num_rows = len(lines) - 2 if len(lines) > 2 else 0
        num_cols = len(headers)
        
        # Build description
        description_parts = [
            f"This table contains {num_rows} rows and {num_cols} columns."
        ]
        
        if headers:
            description_parts.append(f"The columns are: {', '.join(headers)}.")
        
        # Sample first data row if available
        if len(lines) > 2:
            first_data = lines[2]
            cells = [c.strip() for c in first_data.split('|') if c.strip()]
            if cells and headers:
                sample_pairs = [f"{h}: {c}" for h, c in zip(headers, cells) if h and c]
                if sample_pairs:
                    description_parts.append(
                        f"Example row: {', '.join(sample_pairs[:3])}."  # Limit to 3
                    )
        
        return ' '.join(description_parts)
    
    def _create_code_description(
        self, 
        code_content: str, 
        element: Optional[MarkdownElement]
    ) -> str:
        """
        Create natural language description of code block
        Simple rule-based for now, can be enhanced with LLM later
        """
        language = element.metadata.get('language', 'unknown') if element else 'unknown'
        
        lines = [l for l in code_content.split('\n') if l.strip()]
        num_lines = len(lines)
        
        description_parts = [
            f"This is a {language} code block with {num_lines} lines."
        ]
        
        # Detect common patterns
        if language.lower() in ['python', 'py']:
            description_parts.extend(self._analyze_python_code(code_content))
        elif language.lower() in ['javascript', 'js', 'typescript', 'ts']:
            description_parts.extend(self._analyze_javascript_code(code_content))
        elif language.lower() in ['sql']:
            description_parts.extend(self._analyze_sql_code(code_content))
        
        # Check for comments
        if '#' in code_content or '//' in code_content or '/*' in code_content:
            description_parts.append("The code includes comments.")
        
        return ' '.join(description_parts)
    
    def _analyze_python_code(self, code: str) -> List[str]:
        """Analyze Python code for description"""
        features = []
        
        if 'def ' in code:
            # Count functions
            func_count = code.count('def ')
            features.append(f"It defines {func_count} function(s).")
        
        if 'class ' in code:
            class_count = code.count('class ')
            features.append(f"It defines {class_count} class(es).")
        
        if 'import ' in code or 'from ' in code:
            features.append("It includes import statements.")
        
        return features
    
    def _analyze_javascript_code(self, code: str) -> List[str]:
        """Analyze JavaScript code for description"""
        features = []
        
        if 'function ' in code or '=>' in code:
            features.append("It defines function(s).")
        
        if 'class ' in code:
            features.append("It defines class(es).")
        
        if 'const ' in code or 'let ' in code or 'var ' in code:
            features.append("It declares variables.")
        
        if 'import ' in code or 'require(' in code:
            features.append("It includes imports.")
        
        return features
    
    def _analyze_sql_code(self, code: str) -> List[str]:
        """Analyze SQL code for description"""
        features = []
        code_upper = code.upper()
        
        if 'SELECT ' in code_upper:
            features.append("It contains SELECT queries.")
        
        if 'INSERT ' in code_upper:
            features.append("It contains INSERT statements.")
        
        if 'UPDATE ' in code_upper:
            features.append("It contains UPDATE statements.")
        
        if 'DELETE ' in code_upper:
            features.append("It contains DELETE statements.")
        
        if 'CREATE TABLE' in code_upper:
            features.append("It creates table(s).")
        
        return features
    
    def create_summary_representation(
        self, 
        content: str, 
        max_length: int = 200
    ) -> str:
        """
        Create a summary representation for retrieval
        Simple extractive summary for now
        """
        sentences = self._split_sentences_simple(content)
        
        if not sentences:
            return content[:max_length]
        
        # Take first 2-3 sentences
        summary_sentences = sentences[:3]
        summary = ' '.join(summary_sentences)
        
        if len(summary) > max_length:
            summary = summary[:max_length-3] + '...'
        
        return summary
    
    def _split_sentences_simple(self, text: str) -> List[str]:
        """Simple sentence splitter"""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]