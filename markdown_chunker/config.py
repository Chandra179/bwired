from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ChunkingConfig:
    """Default configuration for semantic chunking"""
    
    overlap_tokens: int = 50
    
    # Sentence-aware splitting for text
    use_sentence_boundaries: bool = True
    
    @property
    def safety_buffer(self) -> int:
        """Buffer tokens for separators and safety margin"""
        return 10


@dataclass
class ContextConfig:
    """Configuration for context enhancement"""
    
    include_header_path: bool = True


@dataclass
class EmbeddingConfig:
    """Configuration for embedding model"""
    
    model_name: str = "BAAI/bge-base-en-v1.5"
    model_dim: int = 768
    
    max_token_limit: int = 512
    
    device: str = "cpu"  # or "cuda"
    
    batch_size: int = 128
    use_fp16: bool = True
    show_progress_bar: bool = False


@dataclass
class RAGChunkingConfig:
    """Complete RAG chunking configuration"""
    
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    
    @property
    def max_chunk_size(self) -> int:
        """
        Maximum size for a single chunk (before overlap is added).
        Reserves space for overlap that will be added later.
        """
        return self.embedding.max_token_limit - self.chunking.overlap_tokens - self.chunking.safety_buffer
    
    def __post_init__(self):
        """Cross-validate configurations"""
        if self.chunking.overlap_tokens >= self.embedding.max_token_limit:
            raise ValueError(
                f"overlap_tokens ({self.chunking.overlap_tokens}) must be < "
                f"max_token_limit ({self.embedding.max_token_limit})"
            )
        
        if self.max_chunk_size < 100:
            raise ValueError(
                f"max_chunk_size ({self.max_chunk_size}) is too small. "
                f"Reduce overlap_tokens or increase max_token_limit."
            )


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database"""
    
    url: str = "http://localhost:6333"
    collection_name: str = "markdown_chunks"
    
    grpc_port: int = 6334
    
    distance_metric: str = "Cosine"
    create_if_not_exists: bool = True
    
    storage_batch_size: int = 500