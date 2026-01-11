from typing import List
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

from internal.config import DenseEmbeddingConfig
from internal.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class DenseEmbedder:
    """
    Generate dense embeddings using SentenceTransformer models.
    
    Dense embeddings capture semantic meaning of text in a fixed-length
    vector space. They are used for:
    - Semantic similarity search (find chunks related to query)
    - Link prioritization (score relevance of links to research questions)
    - Vector database storage (Qdrant for hybrid search)
    
    Default model: BAAI/bge-base-en-v1.5 (768 dimensions)
    
    Attributes:
        config: DenseEmbeddingConfig with model settings
        model: Loaded SentenceTransformer model
        tokenizer: HuggingFace tokenizer for the model
        max_seq_length: Maximum token length model can process
    
    Performance:
    - Supports GPU acceleration (device="cuda")
    - FP16 precision reduces memory usage on CUDA
    - Batch encoding for efficiency
    """
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
        
        self.tokenizer = TokenCounter.get_tokenizer(config.model_name)
        self.max_seq_length = self.model.max_seq_length
        
        logger.info(f"Dense model loaded successfully")
        logger.info(f"  Dimension: {self.get_dimension()}")
        logger.info(f"  Max sequence length: {self.max_seq_length}")
    
    def encode(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate dense embeddings for a list of texts.
        
        Each text is converted to a normalized 768-dimensional vector
        that represents its semantic meaning. Vectors are normalized
        to unit length for cosine similarity calculations.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of numpy arrays (embeddings), each with shape (embedding_dim,)
            
        Note:
            - Texts longer than max_seq_length are truncated with warning
            - Batch processing uses config.batch_size for efficiency
            - Embeddings are L2-normalized for cosine similarity
        """
        if not texts:
            return []
        
        logger.info(f"Generating dense embeddings for {len(texts)} texts")
        
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
        """
        Get the dimensionality of the embedding vectors.
        
        Returns:
            Number of dimensions in output vectors (e.g., 768 for bge-base-en-v1.5)
        """
        return self.model.get_sentence_embedding_dimension()