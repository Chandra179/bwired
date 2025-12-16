"""
Token counting utilities using model's tokenizer
"""
from transformers import AutoTokenizer
from typing import List
import logging

logger = logging.getLogger(__name__)


class TokenCounter:
    """Count tokens using a specific model's tokenizer"""
    
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
    
    def split_by_tokens(self, text: str, max_tokens: int) -> List[str]:
        """
        Split text into chunks by token count
        
        Args:
            text: Input text
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        # First try splitting by sentences
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if sentence_tokens > max_tokens:
                # Sentence itself is too long, split by words
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence by words
                word_chunks = self._split_by_words(sentence, max_tokens)
                chunks.extend(word_chunks[:-1])
                if word_chunks:
                    current_chunk = [word_chunks[-1]]
                    current_tokens = self.count_tokens(word_chunks[-1])
            elif current_tokens + sentence_tokens <= max_tokens:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
            else:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        # Simple sentence splitter
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_by_words(self, text: str, max_tokens: int) -> List[str]:
        """Split text by words when sentences are too long"""
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            test_chunk = ' '.join(current_chunk + [word])
            if self.count_tokens(test_chunk) <= max_tokens:
                current_chunk.append(word)
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [word]
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def get_overlap_text(self, text: str, overlap_tokens: int, from_start: bool = False) -> str:
        """
        Extract text with approximately overlap_tokens from start or end
        
        Args:
            text: Input text
            overlap_tokens: Target number of overlap tokens
            from_start: If True, extract from start; else from end
            
        Returns:
            Overlap text
        """
        if not text or overlap_tokens <= 0:
            return ""
        
        words = text.split()
        
        if from_start:
            # Extract from start
            for i in range(1, len(words) + 1):
                chunk = ' '.join(words[:i])
                if self.count_tokens(chunk) >= overlap_tokens:
                    return chunk
            return text
        else:
            # Extract from end
            for i in range(len(words) - 1, -1, -1):
                chunk = ' '.join(words[i:])
                if self.count_tokens(chunk) >= overlap_tokens:
                    return chunk
            return text