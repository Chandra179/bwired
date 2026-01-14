from dataclasses import dataclass
from typing import Optional
import yaml
import logging

logger = logging.getLogger(__name__)

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
    model_dim: int = 768


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
class LLMConfig:
    """Configuration for LLM generation"""
    model: str = "llama3.2"


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector store"""
    url: str = "http://localhost:6333"
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
class Config:
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
    llm: Optional[LLMConfig] = None
    storage: Optional[QdrantConfig] = None
    compression: Optional[CompressionConfig] = None
    
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


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Loads and parses the nested YAML into the Dataclass structure.
    """
    logger.info(f"Loading config from: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    c_raw = data.get('chunking', {})
    e_raw = data.get('embedding', {})
    d_raw = e_raw.get('dense', {})
    s_raw = e_raw.get('sparse', {})
    q_raw = data.get('qdrant', {})
    r_raw = data.get('reranker', {})
    l_raw = data.get('llm', {})

    chunking_cfg = ChunkingConfig(
        max_chunk_size=c_raw.get('chunk_size', 256),
        overlap_tokens=c_raw.get('overlap_tokens', 30),
        include_section_path=c_raw.get('include_header_path', True)
    )
    
    dense_cfg = DenseEmbeddingConfig(
        model_name=d_raw.get('model_name', "BAAI/bge-base-en-v1.5"),
        device=e_raw.get('device', "cuda"),
        batch_size=d_raw.get('batch_size', 30),
        use_fp16=d_raw.get('use_fp16', True),
        show_progress_bar=d_raw.get('show_progress_bar', False),
        model_dim=e_raw.get('model_dim', 768)
    )
    
    sparse_cfg = SparseEmbeddingConfig(
        model_name=s_raw.get('model_name', "prithivida/Splade_PP_en_v1"),
        batch_size=s_raw.get('batch_size', 5),
        threads=s_raw.get('threads', 2)
    )
    
    embedding_cfg = EmbeddingConfig(
        dense=dense_cfg,
        sparse=sparse_cfg,
        embedding_token_limit=e_raw.get('token_limit', 512)
    )
    
    qdrant_cfg = QdrantConfig(
        url=q_raw.get('url', "http://localhost:6333"),
        distance_metric=q_raw.get('distance_metric', "Cosine"),
        grpc_port=q_raw.get('grpc_port', 6334),
        storage_batch_size=q_raw.get('storage_batch_size', 500)
    )

    llm_cfg = LLMConfig(
        model=l_raw.get('model', 'llama3.2')
    )

    reranker_cfg = RerankerConfig(
        model_name=r_raw.get('model_name', 'BAAI/bge-reranker-v2-m3'),
        device=r_raw.get('device', 'cpu'),
        batch_size=r_raw.get('batch_size', 32),
        enabled=True
    )
    
    compression_cfg = CompressionConfig(
        model_name=data.get('compression', {}).get('model_name', 'microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank'),
        compression_ratio=data.get('compression', {}).get('compression_ratio'),
        token_limit=data.get('compression', {}).get('token_limit'),
        device=data.get('compression', {}).get('device', 'cpu')
    )

    return Config(
        chunking=chunking_cfg,
        embedding=embedding_cfg,
        storage=qdrant_cfg,
        reranker=reranker_cfg,
        llm=llm_cfg,
        compression=compression_cfg,
    )