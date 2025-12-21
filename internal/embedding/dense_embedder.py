from typing import List
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

from internal.config import DenseEmbeddingConfig
from internal.utils.token_counter import TokenCounter

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
        
        # Get tokenizer and max sequence length
        self.tokenizer = TokenCounter.get_tokenizer(config.model_name)
        self.max_seq_length = self.model.max_seq_length
        
        logger.info(f"Dense model loaded successfully")
        logger.info(f"  Dimension: {self.get_dimension()}")
        logger.info(f"  Max sequence length: {self.max_seq_length}")
    
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
        
        # Validate and truncate texts if necessary
        validated_texts = TokenCounter.validate_and_truncate_batch(
            texts=texts,
            max_tokens=self.max_seq_length,
            model_name=self.config.model_name,
            tokenizer=self.tokenizer,
            warn_on_truncation=True
        )
        
        embeddings = self.model.encode(
            validated_texts,
            batch_size=self.config.batch_size,
            show_progress_bar=self.config.show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return [embedding for embedding in embeddings]
    
    def get_dimension(self) -> int:
        """Get the dimensionality of the embedding vectors"""
        return self.model.get_sentence_embedding_dimension()