from typing import Dict, Any, List, Optional, Tuple
import logging
import ast
import re
from dataclasses import dataclass

# Assume these exist in your project
from .parser import MarkdownElement
from .config import ContextConfig

logger = logging.getLogger(__name__)

# --- Singleton for Heavy Models ---
class NLPModel:
    _instance = None
    
    @classmethod
    def get(cls):
        if cls._instance is None:
            try:
                import spacy
                logger.info("Loading spaCy model (Singleton)...")
                # Disable components we don't need for speed (parser, lemmatizer)
                cls._instance = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"]) 
            except ImportError:
                logger.warning("spaCy not installed.")
                cls._instance = None
            except OSError:
                logger.warning("spaCy model 'en_core_web_sm' not found.")
                cls._instance = None
        return cls._instance

class ContextEnricher:
    """
    Optimized Context Enricher
    Supports Batch Processing and Lazy Loading
    """
    
    def __init__(self, config: ContextConfig):
        self.config = config
        # Do NOT load spaCy here. Wait until we use it.

    def enrich_chunk(
        self,
        content: str,
        chunk_type: str,
        header_path: List[str],
        document_title: str,
        element: Optional[MarkdownElement] = None,
        surrounding_context: Optional[Dict[str, str]] = None,
        pre_calculated_entities: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        
        enriched = {
            'content': content, 
            'metadata': {},
            'contextualized_content': content 
        }
        
        # --- Metadata Enrichment ---
        if self.config.include_document_context:
            enriched['metadata']['document_title'] = document_title
        
        if self.config.include_header_path and header_path:
            if isinstance(header_path, str):
                path_str = header_path
            else:
                # It is a list, so we join it
                path_str = ' > '.join(header_path)
            
            enriched['metadata']['header_path'] = header_path
            enriched['metadata']['section_context'] = path_str
            
            # Prepend header to embedding content
            enriched['contextualized_content'] = f"{path_str}\n{enriched['contextualized_content']}"

        # --- Context Injection ---
        if self.config.include_surrounding_context and surrounding_context:
            parts = []
            if 'before' in surrounding_context:
                parts.append(f"Context: {surrounding_context['before']}")
            
            parts.append(enriched['contextualized_content'])
            
            if 'after' in surrounding_context:
                parts.append(f"Context: {surrounding_context['after']}")
            
            # We update the embedding text, but 'content' remains clean for display
            enriched['contextualized_content'] = '\n---\n'.join(parts)

        # --- Entity Extraction ---
        if self.config.extract_entities:
            if pre_calculated_entities:
                enriched['metadata']['entities'] = pre_calculated_entities
            elif chunk_type in ['paragraph', 'text']:
                # Fallback for single mode
                nlp = NLPModel.get()
                if nlp:
                    doc = nlp(content[:5000])
                    entities = self._extract_entities_from_doc(doc)
                    if entities:
                        enriched['metadata']['entities'] = entities

        # --- Specialized Descriptions ---
        if chunk_type == 'table' and self.config.create_table_descriptions:
            desc = self._create_table_description(content)
            enriched['metadata']['table_description'] = desc
            # Multi-vector representation (store summary for search, raw for result)
            enriched['search_content'] = desc 

        elif chunk_type == 'code_block' and self.config.create_code_descriptions:
            lang = element.metadata.get('language', '') if element else ''
            desc = self._create_code_description(content, lang)
            enriched['metadata']['code_description'] = desc
            enriched['search_content'] = desc 

        return enriched

    def _extract_entities_from_doc(self, doc) -> Dict[str, List[str]]:
        """Helper to extract entities from a processed Doc"""
        entities = {}
        target_labels = self.config.entity_types or ["ORG", "PRODUCT", "GPE", "PERSON"]
        
        for ent in doc.ents:
            if ent.label_ in target_labels:
                if ent.label_ not in entities:
                    entities[ent.label_] = []
                # Deduplicate
                if ent.text not in entities[ent.label_]:
                    entities[ent.label_].append(ent.text)
        return entities

    def _create_code_description(self, code: str, language: str) -> str:
        """Robust Code Analysis using AST for Python"""
        lines = code.splitlines()
        desc_parts = [f"{language} code block with {len(lines)} lines."]
        
        # 1. Python AST Analysis (Much more accurate than regex)
        if language.lower() in ['python', 'py']:
            try:
                tree = ast.parse(code)
                functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
                
                if classes:
                    desc_parts.append(f"Defines classes: {', '.join(classes[:3])}.")
                if functions:
                    desc_parts.append(f"Defines functions: {', '.join(functions[:5])}.")
                if imports:
                    desc_parts.append(f"Uses libraries: {', '.join(imports[:3])}.")
            except SyntaxError:
                desc_parts.append("Contains Python code fragments.")

        # 2. Fallback / Other Languages (Keep simple regex)
        elif language.lower() in ['sql']:
            keywords = [w for w in ["SELECT", "INSERT", "UPDATE", "DELETE", "JOIN"] if w in code.upper()]
            if keywords:
                desc_parts.append(f"Performs {', '.join(keywords)} operations.")

        return " ".join(desc_parts)

    def _create_table_description(self, content: str) -> str:
        """
        Generate a dense summary for table embedding.
        Format: "Table with columns [A, B, C]. Row 1: [Val1, Val2, Val3]..."
        """
        lines = [l.strip() for l in content.split('\n') if '|' in l]
        if len(lines) < 2:
            return "Table structure."
            
        # Parse Header
        header = [h.strip() for h in lines[0].strip('|').split('|')]
        
        desc = f"Table with columns: {', '.join(header)}."
        
        # Add first 2 rows of data as "context samples" for the embedding
        # This allows vector search to find the table by its content values
        data_rows = lines[2:4] # Skip separator
        for i, row in enumerate(data_rows):
            cells = [c.strip() for c in row.strip('|').split('|')]
            # Zip header with value for semantic context "Price: $10"
            pairs = [f"{h}={c}" for h, c in zip(header, cells) if c]
            desc += f" Row {i+1}: {', '.join(pairs)}."
            
        return desc