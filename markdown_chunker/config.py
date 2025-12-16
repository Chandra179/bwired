"""
Configuration dataclasses for markdown chunking and embedding
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmbeddingConfig:
    """Configuration for embedding model and chunking parameters"""
    
    # Model configuration
    model_name: str = "BAAI/bge-base-en-v1.5"
    model_dim: int = 768
    
    # Token limits
    max_token_limit: int = 512
    target_chunk_size: int = 400
    min_chunk_size: int = 100
    overlap_tokens: int = 50
    
    # Processing configuration
    max_recursion_depth: int = 3
    truncation_buffer: int = 10
    
    # Device configuration
    device: str = "cpu"  # or "cuda" if GPU available
    
    def __post_init__(self):
        """Validate configuration"""
        if self.target_chunk_size >= self.max_token_limit:
            raise ValueError(
                f"target_chunk_size ({self.target_chunk_size}) must be less than "
                f"max_token_limit ({self.max_token_limit})"
            )
        if self.min_chunk_size > self.target_chunk_size:
            raise ValueError(
                f"min_chunk_size ({self.min_chunk_size}) must be less than or equal to "
                f"target_chunk_size ({self.target_chunk_size})"
            )


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database"""
    
    url: str = "http://localhost:6333"
    collection_name: str = "markdown_chunks"
    api_key: Optional[str] = None
    
    # Collection configuration
    distance_metric: str = "Cosine"
    create_if_not_exists: bool = True