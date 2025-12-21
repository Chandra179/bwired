"""
Token counting utilities for embeddings
"""
from transformers import AutoTokenizer
import logging

logger = logging.getLogger(__name__)


class TokenCounter:
    """Count tokens for embedding model"""
    
    def __init__(self, model_name: str):
        """
        Initialize tokenizer for the given model
        
        Args:
            model_name: HuggingFace model ID (e.g., "BAAI/bge-base-en-v1.5")
        """
        logger.info(f"Loading tokenizer for {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model_name = model_name
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text
        
        Args:
            text: Input text
            
        Returns:
            Number of tokens
        """
        if not text or not text.strip():
            return 0
        
        tokens = self.tokenizer.encode(text, add_special_tokens=True)
        return len(tokens)