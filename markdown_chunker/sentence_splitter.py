"""
Sentence boundary detection using spaCy
"""
from typing import List
import logging

try:
    import spacy
    from spacy.language import Language
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

logger = logging.getLogger(__name__)


class SentenceSplitter:
    """Split text into sentences using spaCy"""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize spaCy model for sentence splitting
        
        Args:
            model_name: spaCy model to use
        """
        if not SPACY_AVAILABLE:
            logger.warning("spaCy not available, falling back to simple splitting")
            self.nlp = None
            return
        
        try:
            logger.info(f"Loading spaCy model: {model_name}")
            self.nlp = spacy.load(model_name, disable=["ner", "lemmatizer", "textcat"])
            
            # Only keep sentencizer for performance
            if "sentencizer" not in self.nlp.pipe_names:
                self.nlp.add_pipe("sentencizer")
            
            logger.info("spaCy model loaded successfully")
        except OSError:
            logger.error(
                f"spaCy model '{model_name}' not found. "
                f"Please run: python -m spacy download {model_name}"
            )
            self.nlp = None
    
    def split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []
        
        if self.nlp is None:
            # Fallback to simple splitting
            return self._simple_split(text)
        
        try:
            doc = self.nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            return sentences
        except Exception as e:
            logger.warning(f"spaCy sentence splitting failed: {e}, using fallback")
            return self._simple_split(text)
    
    def split_into_chunks_by_sentences(
        self, 
        text: str, 
        max_tokens: int,
        token_counter
    ) -> List[str]:
        """
        Split text into chunks at sentence boundaries
        
        Args:
            text: Input text
            max_tokens: Maximum tokens per chunk
            token_counter: TokenCounter instance for counting
            
        Returns:
            List of text chunks
        """
        sentences = self.split_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = token_counter.count_tokens(sentence)
            
            # If single sentence is too long, split it by clauses/words
            if sentence_tokens > max_tokens:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split long sentence
                word_chunks = self._split_long_sentence(
                    sentence, max_tokens, token_counter
                )
                chunks.extend(word_chunks)
            
            # Check if adding sentence exceeds limit
            elif current_tokens + sentence_tokens <= max_tokens:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
            else:
                # Flush current chunk and start new
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_long_sentence(
        self, 
        sentence: str, 
        max_tokens: int,
        token_counter
    ) -> List[str]:
        """Split a sentence that's too long by clauses then words"""
        chunks = []
        
        # Try splitting by punctuation (clauses) first
        if len(sentence) > 50:
            import re
            # Split by punctuation but keep the delimiter
            parts = re.split(r'([,;:])', sentence)
            
            if len(parts) > 1:
                # Reassemble parts into chunks that fit
                current_chunk = ""
                for part in parts:
                    test_text = current_chunk + part
                    if token_counter.count_tokens(test_text) <= max_tokens:
                        current_chunk = test_text
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = part
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Check if we successfully reduced the size
                if chunks and all(token_counter.count_tokens(c) <= max_tokens for c in chunks):
                    return chunks
        
        # Fallback to word splitting if clause splitting failed
        words = sentence.split()
        current_chunk = []
        chunks = []
        
        for word in words:
            test_chunk = ' '.join(current_chunk + [word])
            
            if token_counter.count_tokens(test_chunk) <= max_tokens:
                current_chunk.append(word)
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [word]
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [sentence]  # Return original if all else fails
    
    def _simple_split(self, text: str) -> List[str]:
        """Simple fallback sentence splitter using regex"""
        import re
        # Split on .!? followed by whitespace or end of string
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]