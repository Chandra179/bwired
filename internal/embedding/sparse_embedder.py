from typing import List, Dict
import logging
from fastembed import SparseTextEmbedding

from internal.config import SparseEmbeddingConfig
from internal.token_counter import TokenCounter

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
        
        # Get tokenizer for validation
        self.tokenizer = TokenCounter.get_tokenizer(config.model_name)
        self.max_seq_length = TokenCounter.get_max_sequence_length(
            config.model_name, 
            self.tokenizer
        )
        
        logger.info(f"Sparse model loaded successfully")
        logger.info(f"  Vocab size: {self.get_dimension()}")
        logger.info(f"  Max sequence length: {self.max_seq_length}")
    
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
        
        validated_texts = TokenCounter.validate_and_truncate_batch(
            texts=texts,
            max_tokens=self.max_seq_length,
            model_name=self.config.model_name,
            tokenizer=self.tokenizer,
            warn_on_truncation=True
        )
        
        results = []
        batch_size = self.config.batch_size
        
        # Process in batches to avoid high RAM usage
        for i in range(0, len(validated_texts), batch_size):
            batch = validated_texts[i:i + batch_size]
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