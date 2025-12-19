from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ChunkingConfig:
    """Default configuration for semantic chunking, Custom config at .yaml files"""
    
    # Size parameters (in tokens)
    target_chunk_size: int = 400
    
    overlap_tokens: int = 50  # Overlap between adjacent chunks within same section
    
    keep_tables_intact: bool = True
    keep_code_blocks_intact: bool = True
    keep_list_items_together: bool = True
    
    use_sentence_boundaries: bool = True
    
    @property
    def effective_target_size(self) -> int:
        """
        Calculates the space left for new content after reserving overlap space.
        Enforces a minimum floor of 100 tokens to prevent 'micro-chunking'.
        """
        calculated_gap = self.target_chunk_size - self.overlap_tokens - 5 # 5 for safety/separators
        return max(100, calculated_gap)


@dataclass
class ContextConfig:
    """Configuration for context enhancement"""
    
    include_header_path: bool = True


@dataclass
class EmbeddingConfig:
    """Configuration for embedding model"""
    
    # Model configuration
    model_name: str = "BAAI/bge-base-en-v1.5"
    model_dim: int = 768
    
    # Token limits (must match chunking)
    max_token_limit: int = 512
    
    # Device configuration
    device: str = "cpu"  # or "cuda"
    
    # Performance optimization
    batch_size: int = 128  # Increased from 32
    use_fp16: bool = True  # Mixed precision for faster inference on GPU
    show_progress_bar: bool = False  # Show progress during embedding generation


@dataclass
class RAGChunkingConfig:
    """Complete RAG chunking configuration"""
    
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    
    def __post_init__(self):
        """Cross-validate configurations"""
        if self.chunking.effective_target_size > self.embedding.max_token_limit:
            raise ValueError(
                f"chunking.effective_target_chunk_size ({self.chunking.effective_target_size}) must be <= "
                f"embedding.max_token_limit ({self.embedding.max_token_limit})"
            )
        
        if self.chunking.overlap_tokens >= self.chunking.effective_target_size:
            raise ValueError(
                f"chunking.overlap_tokens ({self.chunking.overlap_tokens}) must be < "
                f"chunking.effective_target_chunk_size ({self.chunking.effective_target_size})"
            )


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database"""
    
    # Connection settings
    url: str = "http://localhost:6333"
    collection_name: str = "markdown_chunks"
    
    grpc_port: int = 6334
    
    # Collection configuration
    distance_metric: str = "Cosine"
    create_if_not_exists: bool = True
    
    # Performance optimization
    storage_batch_size: int = 500  # Increased from 100