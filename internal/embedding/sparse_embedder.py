from typing import List, Dict
import logging
from fastembed import SparseTextEmbedding

from internal.config import SparseEmbeddingConfig

logger = logging.getLogger(__name__)


class SparseEmbedder:
    """Generate sparse embeddings using SPLADE models"""
    
    def __init__(self, config: SparseEmbeddingConfig):
        self.config = config
        
        logger.info(f"Loading sparse model: {config.model_name}")
        self.model = SparseTextEmbedding(
            model_name=config.model_name,
            threads=config.threads,
            providers=["CPUExecutionProvider"]
        )
        logger.info(f"Sparse model loaded successfully (vocab size: {self.get_dimension()})")
    
    def encode(self, texts: List[str]) -> List[Dict[str, List]]:
        """
        Generate sparse embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of dictionaries with 'indices' and 'values' keys
        """
        if not texts:
            return []
        
        logger.info(f"Generating sparse embeddings for {len(texts)} texts")
        
        results = []
        batch_size = self.config.batch_size
        
        # Process in batches to avoid high RAM usage
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_generator = self.model.embed(batch, batch_size=batch_size)
            
            for sparse_vec in batch_generator:
                results.append({
                    "indices": sparse_vec.indices.tolist(),
                    "values": sparse_vec.values.tolist()
                })
        
        logger.info(f"Generated {len(results)} sparse vectors")
        return results
    
    def get_dimension(self) -> int:
        """
        Get the dimension (vocabulary size) of the sparse model
        
        Returns:
            Vocabulary size of the tokenizer
        """
        return self.model.model.tokenizer.get_vocab_size