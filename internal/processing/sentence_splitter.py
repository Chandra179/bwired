from typing import List
import logging
from ..token_counter import TokenCounter

try:
    import spacy
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