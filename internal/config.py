from dataclasses import dataclass
from typing import Optional


@dataclass
class BaseSplitterConfig:
    """Base configuration for all splitters"""
    chunk_size: int = 512
    overlap_tokens: int = 0


@dataclass
class MarkdownSplitterConfig(BaseSplitterConfig):
    """Configuration for Markdown splitter"""
    use_sentence_boundaries: bool = True


@dataclass
class ContextConfig:
    """Configuration for context enrichment"""
    include_header_path: bool = True


@dataclass
class DenseEmbeddingConfig:
    """Configuration for dense embedding model (SentenceTransformer)"""
    model_name: str = "BAAI/bge-base-en-v1.5"
    device: str = "cpu"
    batch_size: int = 32
    use_fp16: bool = False
    show_progress_bar: bool = True


@dataclass
class SparseEmbeddingConfig:
    """Configuration for sparse embedding model (SPLADE)"""
    model_name: str = "prithivida/Splade_PP_en_v1"
    batch_size: int = 8
    threads: int = 4


@dataclass
class RerankerConfig:
    """Configuration for reranker model (CrossEncoder)"""
    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "cpu"
    batch_size: int = 32


@dataclass
class EmbeddingConfig:
    """Configuration for all embedding components"""
    dense: DenseEmbeddingConfig
    sparse: SparseEmbeddingConfig
    embedding_token_limit: int = 512
    model_dim: int = 768


@dataclass
class CompressionConfig:
    """Configuration for LLMLingua compression"""
    model_name: str = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
    compression_ratio: Optional[float] = None  # e.g., 0.5 for 50% compression
    token_limit: Optional[int] = None  # Alternative: absolute token target
    device: str = "cpu"


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
    splitter: BaseSplitterConfig
    context: ContextConfig
    embedding: EmbeddingConfig
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        # Ensure chunk_size doesn't exceed embedding model's limit
        if self.splitter.chunk_size > self.embedding.embedding_token_limit:
            raise ValueError(
                f"chunk_size ({self.splitter.chunk_size}) cannot exceed "
                f"embedding_token_limit ({self.embedding.embedding_token_limit})"
            )
        
        # Warn if overlap is too large relative to chunk size
        if self.splitter.overlap_tokens >= self.splitter.chunk_size:
            raise ValueError(
                f"overlap_tokens ({self.splitter.overlap_tokens}) must be "
                f"smaller than chunk_size ({self.splitter.chunk_size})"
            )
    
    @property
    def max_chunk_size(self) -> int:
        """Maximum chunk size for backward compatibility"""
        return self.splitter.chunk_size