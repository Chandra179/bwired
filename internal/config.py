from dataclasses import dataclass
from typing import Optional

@dataclass
class ChunkingConfig:
    max_chunk_size: int = 512
    overlap_tokens: int = 50
    include_section_path: bool = True
    
    def __post_init__(self):
        if self.overlap_tokens >= self.max_chunk_size:
            raise ValueError(
                f"overlap_tokens ({self.overlap_tokens}) must be "
                f"smaller than max_chunk_size ({self.max_chunk_size})"
            )
        
        if self.overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")
        
        if self.max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be positive")
        

@dataclass
class DenseEmbeddingConfig:
    """Configuration for dense embedding model (SentenceTransformer)"""
    model_name: str = "BAAI/bge-base-en-v1.5"
    device: str = "cpu"
    batch_size: int = 32
    use_fp16: bool = False
    show_progress_bar: bool = True
    model_dim: int = 768  # Output dimension


@dataclass
class SparseEmbeddingConfig:
    """Configuration for sparse embedding model (SPLADE)"""
    model_name: str = "prithivida/Splade_PP_en_v1"
    batch_size: int = 8
    threads: int = 4


@dataclass
class EmbeddingConfig:
    """Configuration for embedding components"""
    dense: DenseEmbeddingConfig
    sparse: SparseEmbeddingConfig
    embedding_token_limit: int = 512  # Max tokens the embedding model can handle
    
    def __post_init__(self):
        """Validate embedding configuration"""
        if self.embedding_token_limit <= 0:
            raise ValueError("embedding_token_limit must be positive")


@dataclass
class RerankerConfig:
    """Configuration for reranker model (CrossEncoder)"""
    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "cpu"
    batch_size: int = 32
    enabled: bool = False


@dataclass
class CompressionConfig:
    """Configuration for LLMLingua compression"""
    model_name: str = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
    compression_ratio: Optional[float] = None  # e.g., 0.5 for 50% compression
    token_limit: Optional[int] = None  # Alternative: absolute token target
    device: str = "cpu"
    
    def __post_init__(self):
        """Validate compression parameters"""
        if self.compression_ratio is not None:
            if not 0 < self.compression_ratio < 1:
                raise ValueError("compression_ratio must be between 0 and 1")
        
        if self.token_limit is not None:
            if self.token_limit <= 0:
                raise ValueError("token_limit must be positive")


@dataclass
class ProcessorConfig:
    """Configuration for result processors"""
    enabled: bool = False
    compression: Optional[CompressionConfig] = None


@dataclass
class LLMConfig:
    """Configuration for LLM generation"""
    model: str = "llama3.2"
    temperature: float = 0.1
    system_prompt_path: str = "prompts/system_prompt.j2"
    user_prompt_path: str = "prompts/user_prompt.j2"
    max_tokens: int = 1000
    
    def __post_init__(self):
        """Validate LLM parameters"""
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector store"""
    url: str = "http://localhost:6333"
    collection_name: str = "markdown_chunks"
    distance_metric: str = "Cosine"
    grpc_port: int = 6334
    storage_batch_size: int = 100
    
    def __post_init__(self):
        """Validate Qdrant configuration"""
        valid_metrics = ["Cosine", "Dot", "Euclid", "Manhattan"]
        if self.distance_metric not in valid_metrics:
            raise ValueError(
                f"distance_metric must be one of {valid_metrics}, "
                f"got '{self.distance_metric}'"
            )
        
        if self.storage_batch_size <= 0:
            raise ValueError("storage_batch_size must be positive")


@dataclass
class RAGChunkingConfig:
    """
    Main configuration for RAG chunking system
    
    Simplified to focus on three core concerns:
    1. How to chunk documents (chunking)
    2. How to embed chunks (embedding)
    3. Optional: Processing and storage
    """
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    reranker: Optional[RerankerConfig] = None
    processor: Optional[ProcessorConfig] = None
    llm: Optional[LLMConfig] = None
    storage: Optional[QdrantConfig] = None
    
    def __post_init__(self):
        """Validate cross-config constraints"""
        # Ensure chunk size doesn't exceed embedding model's token limit
        if self.chunking.max_chunk_size > self.embedding.embedding_token_limit:
            raise ValueError(
                f"max_chunk_size ({self.chunking.max_chunk_size}) cannot exceed "
                f"embedding_token_limit ({self.embedding.embedding_token_limit})"
            )
        
        # Warn if overlap is significant relative to chunk size
        overlap_ratio = self.chunking.overlap_tokens / self.chunking.max_chunk_size
        if overlap_ratio > 0.5:
            import warnings
            warnings.warn(
                f"overlap_tokens is {overlap_ratio:.0%} of max_chunk_size. "
                "This may result in highly redundant chunks.",
                UserWarning
            )