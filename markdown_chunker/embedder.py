from typing import List
import torch
from transformers import AutoTokenizer, AutoModel
import logging
import numpy as np

from .config import EmbeddingConfig

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using specified model"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.device = torch.device(config.device)
        
        logger.info(f"Loading embedding model: {config.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        self.model = AutoModel.from_pretrained(config.model_name)
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"Model loaded on device: {self.device}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        return self.generate_embeddings([text])[0]
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        all_embeddings = []
        
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                logger.debug(f"Processing batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")
                
                # Tokenize
                encoded = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.config.max_token_limit,
                    return_tensors='pt'
                )
                
                # Move to device
                encoded = {k: v.to(self.device) for k, v in encoded.items()}
                
                # Generate embeddings
                outputs = self.model(**encoded)
                
                # Use mean pooling
                embeddings = self._mean_pooling(outputs, encoded['attention_mask'])
                
                # Normalize embeddings
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                
                # Convert to numpy and store
                batch_embeddings = embeddings.cpu().numpy()
                all_embeddings.extend(batch_embeddings)
        
        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings
    
    def _mean_pooling(self, model_output, attention_mask):
        """
        Perform mean pooling on token embeddings
        
        Args:
            model_output: Model output containing token embeddings
            attention_mask: Attention mask
            
        Returns:
            Pooled embeddings
        """
        token_embeddings = model_output[0]  # First element contains token embeddings
        
        # Expand attention mask to match token embeddings dimensions
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        
        # Sum embeddings and divide by mask sum
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        
        return sum_embeddings / sum_mask
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors"""
        return self.config.model_dim