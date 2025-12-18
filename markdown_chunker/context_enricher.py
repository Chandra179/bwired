from typing import Dict, Any, List, Optional
import logging

from .config import ContextConfig

logger = logging.getLogger(__name__)

class ContextEnricher:
    """
    Optimized Context Enricher
    Supports Batch Processing and Lazy Loading
    """
    
    def __init__(self, config: ContextConfig):
        self.config = config

    def enrich_chunk(
        self,
        content: str,
        header_path: List[str],
        document_title: str,
        surrounding_context: Optional[Dict[str, str]] = None
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

        return enriched