from typing import List, Tuple
import logging
import numpy as np
from sentence_transformers import CrossEncoder

from markdown_chunker.config import RerankerConfig

logger = logging.getLogger(__name__)


class Reranker:
    """Rerank search results using CrossEncoder models"""
    
    def __init__(self, config: RerankerConfig):
        self.config = config
        
        logger.info(f"Loading reranker model: {config.model_name}")
        self.model = CrossEncoder(config.model_name, device=config.device)
        logger.info("Reranker model loaded successfully")
    
    def predict(self, query_doc_pairs: List[List[str]]) -> np.ndarray:
        """
        Score query-document pairs
        
        Args:
            query_doc_pairs: List of [query, document] pairs
            
        Returns:
            Array of relevance scores
        """
        if not query_doc_pairs:
            return np.array([])
        
        logger.info(f"Reranking {len(query_doc_pairs)} query-document pairs")
        scores = self.model.predict(query_doc_pairs, batch_size=self.config.batch_size)
        return scores