from typing import List, Dict, Any
import logging
import warnings
from llmlingua import PromptCompressor

from ..config import CompressionConfig
from ..utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class ContextCompressor():
    """Compresses search results using LLMLingua-2"""
    
    def __init__(self, config: CompressionConfig):
        """
        Initialize LLM Context Compressor
        
        Args:
            config: Compression configuration
        """
        self.config = config
        self.compressor = None
        self.tokenizer = None
        self.max_seq_length = 512
        
        logger.info(f"Initializing ContextCompressor with model: {config.model_name}")
        try:
            self.compressor = PromptCompressor(
                model_name=config.model_name,
                device_map=config.device,
                use_llmlingua2=True,
            )
            
            logger.info("Loading tokenizer for token counting...")
            self.tokenizer = TokenCounter.get_tokenizer(config.model_name)
            self.max_seq_length = TokenCounter.get_max_sequence_length(
                config.model_name,
                self.tokenizer
            )
            
            logger.info("LLMLingua compressor initialized successfully")
            logger.info(f"  Max sequence length: {self.max_seq_length}")
        except Exception as e:
            logger.error(f"Failed to initialize LLMLingua: {e}")
            logger.warning("Compression will be disabled")
            self.compressor = None
            self.tokenizer = None
    
    def _combine_chunks(self, results: List[Dict[str, Any]]) -> str:
        """Combine chunks with structured separators (unchanged)"""
        combined_parts = []
        
        for idx, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            section = metadata.get("section_path", "unknown")
            
            separator = f"Section: {section}"
            combined_parts.append(separator)
            combined_parts.append(result.get("content", ""))
            combined_parts.append("")  # Empty line between chunks
        
        return "\n".join(combined_parts)
    
    def _compress_with_chunking(self, text: str, target_tokens: int) -> str:
        """
        Compress text by splitting into processable chunks if needed
        """
        token_count = TokenCounter.count_tokens(
            text,
            self.config.model_name,
            self.tokenizer
        )
        
        logger.info(f"Input text: {token_count} tokens")
        
        if token_count <= self.max_seq_length:
            logger.info(f"Input within model limits, compressing directly...")
            return self._compress_single(text, target_tokens)
        
        logger.warning(
            f"Input ({token_count} tokens) exceeds model max ({self.max_seq_length} tokens)"
        )
        
        # Strategy 1: Try compressing anyway
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
            self.config.model_name,
            self.tokenizer
        )
        return self._compress_single(truncated_text, target_tokens)
    
    def _compress_single(self, text: str, target_tokens: int) -> str:
        """Compress a single text segment"""
        
        kwargs = {}
        
        if target_tokens:
            kwargs["target_token"] = target_tokens
        elif self.config.compression_ratio is not None:
            kwargs["rate"] = self.config.compression_ratio
        else:
            kwargs["rate"] = 0.5
        
        logger.info(f"Compressing with params: {kwargs}")
        
        # Suppress transformers warning about sequence length
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message='Token indices sequence length is longer than'
            )
            
            compressed_result = self.compressor.compress_prompt(
                text,
                instruction="",
                question="",
                **kwargs
            )
        
        compressed_text = compressed_result["compressed_prompt"]
        
        original_tokens = TokenCounter.count_tokens(
            text,
            self.config.model_name,
            self.tokenizer
        )
        compressed_tokens = TokenCounter.count_tokens(
            compressed_text,
            self.config.model_name,
            self.tokenizer
        )
        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 0
        
        logger.info(f"Compression complete: {original_tokens} → {compressed_tokens} tokens (~{ratio:.2%})")
        
        return compressed_text
    
    def _compress(self, text: str) -> str:
        """Compress text using LLMLingua"""
        # REMOVED intermediate variable
        
        # Determine target tokens
        target_tokens = None
        if self.config.token_limit is not None:
            target_tokens = min(self.config.token_limit, self.max_seq_length // 2)
            logger.info(f"Target token limit: {target_tokens}")
        elif self.config.compression_ratio is not None:
            token_count = TokenCounter.count_tokens(
                text,
                self.config.model_name,
                self.tokenizer
            )
            target_tokens = int(token_count * self.config.compression_ratio)
            target_tokens = min(target_tokens, self.max_seq_length // 2)
            logger.info(f"Calculated target tokens: {target_tokens} (ratio: {self.config.compression_ratio})")
        
        try:
            return self._compress_with_chunking(text, target_tokens)
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            logger.warning("Returning original text")
            return text
    
    def process(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process search results by compressing them (unchanged)"""
        
        if not results:
            logger.warning("No results to compress")
            return {
                "results": results,
                "compressed_context": None
            }
        
        logger.info(f"Compressing {len(results)} chunks")
        
        combined_text = self._combine_chunks(results)
        compressed_text = self._compress(combined_text)
        
        return {
            "results": results,
            "compressed_context": compressed_text
        }