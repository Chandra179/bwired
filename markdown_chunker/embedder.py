from typing import List
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

from .config import EmbeddingConfig

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using sentence-transformers (optimized)"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        
        logger.info(f"Loading embedding model: {config.model_name}")
        logger.info(f"Device: {config.device}")
        logger.info(f"Batch size: {config.batch_size}")
        logger.info(f"FP16 enabled: {config.use_fp16 and config.device == 'cuda'}")
        
        # Load model using sentence-transformers (more optimized)
        self.model = SentenceTransformer(config.model_name, device=config.device)
        
        # Enable FP16 if on GPU and requested
        if config.device == "cuda" and config.use_fp16:
            try:
                self.model = self.model.half()
                logger.info("Model converted to FP16 for faster inference")
            except Exception as e:
                logger.warning(f"Could not convert to FP16: {e}. Using FP32.")
        
        logger.info(f"Model loaded successfully")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        return self.generate_embeddings([text])[0]
    
    def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts using optimized batch processing
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors as numpy arrays
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        logger.debug(f"Using batch size: {self.config.batch_size}")
        
        # Use sentence-transformers encode method (handles batching internally)
        # This is significantly faster than manual batching with raw transformers
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=self.config.show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True  # Already normalized by sentence-transformers
        )
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Convert to list of numpy arrays for consistency
        return [embedding for embedding in embeddings]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        return self.model.get_sentence_embedding_dimension()