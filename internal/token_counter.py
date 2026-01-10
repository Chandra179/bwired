"""
Token counting utilities for various embedding and language models
"""
from typing import Optional, List, Union
import logging
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)


class TokenCounter:
    """Universal token counter that caches tokenizers for reuse.
    
    Supports class method for counting tokens:
    - Class method: TokenCounter.count_tokens(text, model_name, tokenizer)
    """
    
    _tokenizer_cache = {}
    
    def __init__(self, model_name: str):
        """
        Initialize token counter for a specific model (for chunker usage).
        
        Args:
            model_name: HuggingFace model ID
        """
        self.model_name = model_name
        self.tokenizer = self.get_tokenizer(model_name)
    
    @classmethod
    def get_tokenizer(cls, model_name: str) -> Optional[AutoTokenizer]:
        """
        Get or load a tokenizer, with caching
        
        Args:
            model_name: HuggingFace model name
            
        Returns:
            Tokenizer instance or None if loading fails
        """
        if model_name in cls._tokenizer_cache:
            return cls._tokenizer_cache[model_name]
        
        try:
            logger.info(f"Loading tokenizer for: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            cls._tokenizer_cache[model_name] = tokenizer
            logger.info(f"Tokenizer loaded and cached: {model_name}")
            return tokenizer
        except Exception as e:
            logger.warning(f"Failed to load tokenizer for {model_name}: {e}")
            return None
    
    @classmethod
    def count_tokens(
        cls, 
        text: Union[str, List[str]], 
        model_name: str,
        tokenizer: Optional[AutoTokenizer] = None
    ) -> Union[int, List[int]]:
        """
        Count tokens in text(s) using the model's tokenizer
        
        Args:
            text: Single text string or list of texts
            model_name: HuggingFace model name
            tokenizer: Optional pre-loaded tokenizer
            
        Returns:
            Token count(s) - int for single text, list for multiple texts
        """
        # Get tokenizer
        if tokenizer is None:
            tokenizer = cls.get_tokenizer(model_name)
        
        if tokenizer is None:
            # Fallback to rough estimate
            logger.warning("Using rough token estimation (4 chars per token)")
            if isinstance(text, str):
                return len(text) // 4
            else:
                return [len(t) // 4 for t in text]
        
        # Count tokens
        try:
            if isinstance(text, str):
                tokens = tokenizer.encode(text, add_special_tokens=True)
                return len(tokens)
            else:
                counts = []
                for t in text:
                    tokens = tokenizer.encode(t, add_special_tokens=True)
                    counts.append(len(tokens))
                return counts
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, using rough estimate")
            if isinstance(text, str):
                return len(text) // 4
            else:
                return [len(t) // 4 for t in text]
    
    @classmethod
    def truncate_text(
        cls,
        text: str,
        max_tokens: int,
        model_name: str,
        tokenizer: Optional[AutoTokenizer] = None
    ) -> str:
        """
        Truncate text to fit within max_tokens
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            model_name: HuggingFace model name
            tokenizer: Optional pre-loaded tokenizer
            
        Returns:
            Truncated text
        """
        # Get tokenizer
        if tokenizer is None:
            tokenizer = cls.get_tokenizer(model_name)
        
        if tokenizer is None:
            # Fallback to character-based truncation
            max_chars = max_tokens * 4
            logger.warning(f"Using character-based truncation: {max_chars} chars")
            return text[:max_chars] if len(text) > max_chars else text
        
        try:
            # Encode and truncate
            tokens = tokenizer.encode(
                text,
                add_special_tokens=True,
                truncation=True,
                max_length=max_tokens
            )
            
            # Decode back to text
            truncated = tokenizer.decode(tokens, skip_special_tokens=True)
            
            if len(tokens) < len(tokenizer.encode(text, add_special_tokens=True)):
                logger.debug(f"Text truncated from {len(text)} to {len(truncated)} characters")
            
            return truncated
            
        except Exception as e:
            logger.warning(f"Token-based truncation failed: {e}, using character truncation")
            max_chars = max_tokens * 4
            return text[:max_chars] if len(text) > max_chars else text
    
    @classmethod
    def validate_and_truncate_batch(
        cls,
        texts: List[str],
        max_tokens: int,
        model_name: str,
        tokenizer: Optional[AutoTokenizer] = None,
        warn_on_truncation: bool = True
    ) -> List[str]:
        """
        Validate and truncate a batch of texts
        
        Args:
            texts: List of texts to validate
            max_tokens: Maximum tokens per text
            model_name: HuggingFace model name
            tokenizer: Optional pre-loaded tokenizer
            warn_on_truncation: Whether to log warnings for truncated texts
            
        Returns:
            List of validated/truncated texts
        """
        if not texts:
            return texts
        
        # Get tokenizer
        if tokenizer is None:
            tokenizer = cls.get_tokenizer(model_name)
        
        # Count tokens for all texts
        token_counts = cls.count_tokens(texts, model_name, tokenizer)
        
        # Check which texts need truncation
        needs_truncation = [count > max_tokens for count in token_counts]
        
        if any(needs_truncation) and warn_on_truncation:
            truncated_count = sum(needs_truncation)
            logger.warning(
                f"{truncated_count}/{len(texts)} texts exceed {max_tokens} tokens and will be truncated"
            )
        
        # Truncate texts that exceed limit
        result = []
        for i, text in enumerate(texts):
            if needs_truncation[i]:
                truncated = cls.truncate_text(text, max_tokens, model_name, tokenizer)
                result.append(truncated)
            else:
                result.append(text)
        
        return result
    
    @classmethod
    def get_max_sequence_length(cls, model_name: str, tokenizer: Optional[AutoTokenizer] = None) -> int:
        """
        Get the maximum sequence length for a model
        
        Args:
            model_name: HuggingFace model name
            tokenizer: Optional pre-loaded tokenizer
            
        Returns:
            Maximum sequence length, defaults to 512 if unknown
        """
        if tokenizer is None:
            tokenizer = cls.get_tokenizer(model_name)
        
        if tokenizer is None:
            logger.warning(f"Cannot determine max length for {model_name}, using default 512")
            return 512
        
        try:
            # Try to get model_max_length
            max_length = tokenizer.model_max_length
            
            # Some tokenizers return very large values (1000000000000000019884624838656)
            # In that case, use a reasonable default
            if max_length > 100000:
                logger.warning(f"Model max length too large ({max_length}), using default 512")
                return 512
            
            return max_length
        except Exception as e:
            logger.warning(f"Failed to get max length: {e}, using default 512")
            return 512