from dataclasses import dataclass


@dataclass
class ChunkingConfig:
    """Configuration for chunking behavior"""
    chunk_size: int = 512  # NEW: Target size for chunks (must be <= embedding_token_limit)
    overlap_tokens: int = 0
    use_sentence_boundaries: bool = True


@dataclass
class ContextConfig:
    """Configuration for context enrichment"""
    include_header_path: bool = True


@dataclass
class EmbeddingConfig:
    """Configuration for embedding model"""
    dense_model_name: str = "BAAI/bge-base-en-v1.5"
    sparse_model_name: str = "prithivida/Splade_PP_en_v1"
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    model_dim: int = 768
    embedding_token_limit: int = 512
    device: str = "cpu"
    batch_size: int = 32
    use_fp16: bool = False
    show_progress_bar: bool = True


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector store"""
    url: str = "http://localhost:6333"
    collection_name: str = "markdown_chunks"
    distance_metric: str = "Cosine"
    grpc_port: int = 6334
    storage_batch_size: int = 100


@dataclass
class RAGChunkingConfig:
    """Main configuration container with validation"""
    chunking: ChunkingConfig
    context: ContextConfig
    embedding: EmbeddingConfig
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        # Ensure chunk_size doesn't exceed embedding model's limit
        if self.chunking.chunk_size > self.embedding.embedding_token_limit:
            raise ValueError(
                f"chunk_size ({self.chunking.chunk_size}) cannot exceed "
                f"embedding_token_limit ({self.embedding.embedding_token_limit})"
            )
        
        # Warn if overlap is too large relative to chunk size
        if self.chunking.overlap_tokens >= self.chunking.chunk_size:
            raise ValueError(
                f"overlap_tokens ({self.chunking.overlap_tokens}) must be "
                f"smaller than chunk_size ({self.chunking.chunk_size})"
            )
    
    @property
    def max_chunk_size(self) -> int:
        """Maximum chunk size for backward compatibility"""
        return self.chunking.chunk_size