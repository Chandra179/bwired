from typing import List, Dict, Any
import logging
import warnings
from llmlingua import PromptCompressor

from .base_processor import BaseProcessor
from ..config import ProcessorConfig
from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class LLMLinguaCompressor(BaseProcessor):
    """Compresses search results using LLMLingua-2"""
    
    def __init__(self, config: ProcessorConfig):
        """
        Initialize LLMLingua compressor
        
        Args:
            config: Processor configuration
        """
        self.config = config
        self.compressor = None
        self.tokenizer = None
        self.max_seq_length = 512  # LLMLingua-2 BERT base default
        
        if config.enabled and config.compression:
            logger.info(f"Initializing LLMLingua with model: {config.compression.model_name}")
            try:
                self.compressor = PromptCompressor(
                    model_name=config.compression.model_name,
                    device_map=config.compression.device,
                    use_llmlingua2=True,  # Use LLMLingua-2 API
                )
                
                # Load tokenizer for accurate token counting
                logger.info("Loading tokenizer for token counting...")
                self.tokenizer = TokenCounter.get_tokenizer(config.compression.model_name)
                self.max_seq_length = TokenCounter.get_max_sequence_length(
                    config.compression.model_name,
                    self.tokenizer
                )
                
                logger.info("LLMLingua compressor initialized successfully")
                logger.info(f"  Max sequence length: {self.max_seq_length}")
            except Exception as e:
                logger.error(f"Failed to initialize LLMLingua: {e}")
                logger.warning("Compression will be disabled")
                self.compressor = None
                self.tokenizer = None
    
    def is_enabled(self) -> bool:
        """Check if compression is enabled"""
        return self.config.enabled and self.compressor is not None
    
    def _combine_chunks(self, results: List[Dict[str, Any]]) -> str:
        """
        Combine chunks with structured separators
        
        Args:
            results: List of search results
            
        Returns:
            Combined text with separators
        """
        combined_parts = []
        total_chunks = len(results)
        
        for idx, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            doc_path = metadata.get("document_path", "unknown")
            section = metadata.get("section_path", "unknown")
            
            separator = f"=== Document: {doc_path} | Section: {section} | Chunk {idx}/{total_chunks} ==="
            combined_parts.append(separator)
            combined_parts.append(result.get("content", ""))
            combined_parts.append("")  # Empty line between chunks
        
        return "\n".join(combined_parts)
    
    def _compress_with_chunking(self, text: str, target_tokens: int) -> str:
        """
        Compress text by splitting into processable chunks if needed
        
        Args:
            text: Text to compress
            target_tokens: Target token count after compression
            
        Returns:
            Compressed text
        """
        compression_config = self.config.compression
        
        # Count tokens
        token_count = TokenCounter.count_tokens(
            text,
            compression_config.model_name,
            self.tokenizer
        )
        
        logger.info(f"Input text: {token_count} tokens")
        
        # If input is within limits, compress directly
        if token_count <= self.max_seq_length:
            logger.info(f"Input within model limits, compressing directly...")
            return self._compress_single(text, target_tokens)
        
        # Input exceeds model limits - need to handle differently
        logger.warning(
            f"Input ({token_count} tokens) exceeds model max ({self.max_seq_length} tokens)"
        )
        
        # Strategy 1: Try compressing anyway (LLMLingua may handle it internally)
        # This produces the warning but often works
        logger.info("Attempting compression (LLMLingua will handle long input internally)...")
        try:
            compressed = self._compress_single(text, target_tokens)
            return compressed
        except Exception as e:
            logger.warning(f"Direct compression failed: {e}")
        
        # Strategy 2: Pre-truncate as fallback
        logger.info(f"Fallback: Truncating input to {self.max_seq_length} tokens before compression")
        truncated_text = TokenCounter.truncate_text(
            text,
            self.max_seq_length,
            compression_config.model_name,
            self.tokenizer
        )
        return self._compress_single(truncated_text, target_tokens)
    
    def _compress_single(self, text: str, target_tokens: int) -> str:
        """
        Compress a single text segment
        
        Args:
            text: Text to compress
            target_tokens: Target token count
            
        Returns:
            Compressed text
        """
        compression_config = self.config.compression
        
        # Determine compression parameters
        kwargs = {}
        
        if target_tokens:
            kwargs["target_token"] = target_tokens
        elif compression_config.compression_ratio is not None:
            kwargs["rate"] = compression_config.compression_ratio
        else:
            kwargs["rate"] = 0.5
        
        logger.info(f"Compressing with params: {kwargs}")
        
        # Suppress transformers warning about sequence length
        # LLMLingua handles long sequences internally with sliding windows
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message='Token indices sequence length is longer than'
            )
            
            compressed_result = self.compressor.compress_prompt(
                text,
                instruction="",  # Empty instruction for general compression
                question="",     # Empty question for general compression
                **kwargs
            )
        
        compressed_text = compressed_result["compressed_prompt"]
        
        # Calculate compression stats
        original_tokens = TokenCounter.count_tokens(
            text,
            compression_config.model_name,
            self.tokenizer
        )
        compressed_tokens = TokenCounter.count_tokens(
            compressed_text,
            compression_config.model_name,
            self.tokenizer
        )
        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 0
        
        logger.info(f"Compression complete: {original_tokens} -> {compressed_tokens} tokens (~{ratio:.2%})")
        
        return compressed_text
    
    def _compress(self, text: str) -> str:
        """
        Compress text using LLMLingua
        
        Args:
            text: Text to compress
            
        Returns:
            Compressed text
        """
        compression_config = self.config.compression
        
        # Determine target tokens
        target_tokens = None
        if compression_config.token_limit is not None:
            target_tokens = min(compression_config.token_limit, self.max_seq_length // 2)
            logger.info(f"Target token limit: {target_tokens}")
        elif compression_config.compression_ratio is not None:
            # Calculate target, but don't exceed model limits
            token_count = TokenCounter.count_tokens(
                text,
                compression_config.model_name,
                self.tokenizer
            )
            target_tokens = int(token_count * compression_config.compression_ratio)
            target_tokens = min(target_tokens, self.max_seq_length // 2)
            logger.info(f"Calculated target tokens: {target_tokens} (ratio: {compression_config.compression_ratio})")
        
        try:
            return self._compress_with_chunking(text, target_tokens)
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            logger.warning("Returning original text")
            return text
    
    def process(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process search results by compressing them
        
        Args:
            results: List of search results with scores, content, and metadata
            
        Returns:
            Dictionary with original results and compressed context
        """
        if not self.is_enabled():
            logger.debug("Compression disabled, returning original results only")
            return {
                "results": results,
                "compressed_context": None
            }
        
        if not results:
            logger.warning("No results to compress")
            return {
                "results": results,
                "compressed_context": None
            }
        
        logger.info(f"Compressing {len(results)} chunks")
        
        # Combine all chunks with separators
        combined_text = self._combine_chunks(results)
        
        # Compress the combined text
        compressed_text = self._compress(combined_text)
        
        return {
            "results": results,
            "compressed_context": compressed_text
        }