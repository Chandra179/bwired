"""
Token counting utilities for embeddings
"""
from transformers import AutoTokenizer
from typing import List
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
    
    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """
        Count tokens for multiple texts efficiently
        
        Args:
            texts: List of input texts
            
        Returns:
            List of token counts
        """
        if not texts:
            return []
        
        encodings = self.tokenizer(texts, add_special_tokens=True)
        return [len(ids) for ids in encodings['input_ids']]
    
    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to maximum token count
        
        Args:
            text: Input text
            max_tokens: Maximum number of tokens
            
        Returns:
            Truncated text
        """
        if not text:
            return ""
        
        tokens = self.tokenizer.encode(text, add_special_tokens=True)
        
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens, skip_special_tokens=True)
    
    def estimate_tokens(self, text: str) -> int:
        """
        Fast token estimation without full tokenization
        Approximation: 1 token ≈ 0.75 words (for English)
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        words = len(text.split())
        return int(words * 1.3)  # ~1.3 tokens per word on average