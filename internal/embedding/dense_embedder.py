from typing import List
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

from internal.config import DenseEmbeddingConfig

logger = logging.getLogger(__name__)


class DenseEmbedder:
    """Generate dense embeddings using SentenceTransformer models"""
    
    def __init__(self, config: DenseEmbeddingConfig):
        self.config = config
        
        logger.info(f"Loading dense model: {config.model_name}")
        self.model = SentenceTransformer(config.model_name, device=config.device)
        
        if config.device == "cuda" and config.use_fp16:
            try:
                self.model = self.model.half()
                logger.info("Dense model converted to FP16")
            except Exception as e:
                logger.warning(f"FP16 conversion failed: {e}")
        
        logger.info(f"Dense model loaded successfully (dimension: {self.get_dimension()})")
    
    def encode(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate dense embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of numpy arrays (embeddings)
        """
        if not texts:
            return []
        
        logger.info(f"Generating dense embeddings for {len(texts)} texts")
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=self.config.show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return [embedding for embedding in embeddings]
    
    def get_dimension(self) -> int:
        """Get the dimensionality of the embedding vectors"""
        return self.model.get_sentence_embedding_dimension()