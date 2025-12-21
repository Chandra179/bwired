from typing import List, Dict
import os
import logging
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from fastembed import SparseTextEmbedding

from markdown_chunker.config import EmbeddingConfig

logger = logging.getLogger(__name__)

# Handle OpenMP conflicts before other imports if possible, 
# or set this inside the class before loading models
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

class EmbeddingGenerator:
    """Generate Dense (SentenceTransformer) and Sparse (SPLADE) embeddings"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
    
        logger.info(f"Loading dense model: {config.dense_model_name}")
        self.dense_model = SentenceTransformer(config.dense_model_name, device=config.device)
        
        logger.info(f"Loading reranker model: {config.reranker_model_name}")
        self.reranker = CrossEncoder(config.reranker_model_name, device=config.device)
        
        if config.device == "cuda" and config.use_fp16:
            try:
                self.dense_model = self.dense_model.half()
                logger.info("Dense model converted to FP16")
            except Exception as e:
                logger.warning(f"FP16 failed: {e}")
        
        sparse_model_name = getattr(config, "sparse_model_name", "prithivida/Splade_PP_en_v1")
        logger.info(f"Loading sparse model: {sparse_model_name}")
        
        self.sparse_model = SparseTextEmbedding(
            model_name=sparse_model_name, 
            threads=4,
            providers=["CPUExecutionProvider"]
        )
        
        logger.info("Models loaded successfully")
    
    def generate_dense_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate Dense Embeddings (unchanged)"""
        if not texts:
            return []
        
        logger.info(f"Generating dense embeddings for {len(texts)} texts")
        embeddings = self.dense_model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=self.config.show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return [embedding for embedding in embeddings]

    def generate_sparse_embeddings(self, texts: List[str]) -> List[Dict[str, List]]:
        """
        Generate Sparse Embeddings (SPLADE) for Hybrid Search.
        """
        if not texts:
            return []
            
        logger.info(f"Generating sparse embeddings for {len(texts)} texts")
        
        # fastembed returns a generator, so we convert to list
        # We process in batches to avoid high RAM usage if texts list is huge
        results = []
        safe_batch_size = 8
        
        for i in range(0, len(texts), safe_batch_size):
            batch = texts[i : i + safe_batch_size]
            batch_generator = self.sparse_model.embed(batch, batch_size=safe_batch_size)
            for sparse_vec in batch_generator:
                results.append({
                    "indices": sparse_vec.indices.tolist(),
                    "values": sparse_vec.values.tolist()
                })
                
        logger.info(f"Generated {len(results)} sparse vectors")
        return results

    def get_dense_embedding_dimension(self) -> int:
        return self.dense_model.get_sentence_embedding_dimension()
    
    
    def get_sparse_embedding_dimension(self) -> int:
        """
        Returns the dimension (vocabulary size) of the sparse model.
        In SPLADE, the dimension is the size of the tokenizer's vocabulary.
        """
        # fastembed stores the underlying model information in the .model attribute
        # The dimension corresponds to the number of tokens in the vocabulary
        return self.sparse_model.model.tokenizer.vocab_size