from dataclasses import dataclass, field
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
class PostgresConfig:
    """Configuration for PostgreSQL database"""
    host: str = "localhost"
    port: int = 5432
    database: str = "bwired_research"
    user: str = "bwired"
    password: str = ""

    def __post_init__(self):
        """Validate PostgreSQL configuration"""
        if self.port <= 0 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if not self.database:
            raise ValueError("database name cannot be empty")


@dataclass
class SearXNGConfig:
    """Configuration for SearXNG search engine"""
    url: str = "http://localhost:8080"
    timeout: int = 30
    max_results_per_query: int = 10

    def __post_init__(self):
        """Validate SearXNG configuration"""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_results_per_query <= 0:
            raise ValueError("max_results_per_query must be positive")


@dataclass
class CrawlingConfig:
    """Configuration for web crawling"""
    max_urls_per_domain: int = 5
    relevance_threshold: int = 50
    timeout: int = 30
    user_agent: str = "BwiredResearchBot/1.0"

    def __post_init__(self):
        """Validate crawling configuration"""
        if self.max_urls_per_domain <= 0:
            raise ValueError("max_urls_per_domain must be positive")
        if not 0 <= self.relevance_threshold <= 100:
            raise ValueError("relevance_threshold must be between 0 and 100")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class OllamaLLMConfig:
    """Configuration for Ollama LLM provider"""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2"
    timeout: int = 120

    def __post_init__(self):
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class OpenAILLMConfig:
    """Configuration for OpenAI LLM provider"""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    timeout: int = 120

    def __post_init__(self):
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class LLMProviderConfig:
    """Configuration for LLM providers used in extraction"""
    provider: str = "ollama"  # "ollama" or "openai"
    ollama: OllamaLLMConfig = field(default_factory=OllamaLLMConfig)
    openai: OpenAILLMConfig = field(default_factory=OpenAILLMConfig)

    def __post_init__(self):
        valid_providers = {"ollama", "openai"}
        if self.provider not in valid_providers:
            raise ValueError(f"provider must be one of {valid_providers}")


@dataclass
class ExtractionConfig:
    """Configuration for fact extraction"""
    batch_size: int = 5
    confidence_threshold: float = 0.7
    llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    retrieval_top_k: int = 10  # Number of chunks to retrieve per question

    def __post_init__(self):
        """Validate extraction configuration"""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if self.retrieval_top_k <= 0:
            raise ValueError("retrieval_top_k must be positive")


@dataclass
class SynthesisConfig:
    """Configuration for report synthesis"""
    llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    max_facts_per_section: int = 20
    min_confidence: float = 0.7
    include_citations: bool = True
    report_format: str = "markdown"  # Single format for MVP
    citation_format: str = "url"  # "url" for [source_url]

    def __post_init__(self):
        if self.max_facts_per_section <= 0:
            raise ValueError("max_facts_per_section must be positive")
        valid_formats = {"markdown"}
        if self.report_format not in valid_formats:
            raise ValueError(f"report_format must be one of {valid_formats}")


@dataclass
class ResearchConfig:
    """Configuration for deep research system"""
    postgres: PostgresConfig
    searxng: SearXNGConfig
    crawling: CrawlingConfig
    extraction: ExtractionConfig
    synthesis: SynthesisConfig = field(default_factory=lambda: SynthesisConfig(llm=LLMProviderConfig()))
    max_concurrent_sessions: int = 5

    def __post_init__(self):
        if self.max_concurrent_sessions <= 0:
            raise ValueError("max_concurrent_sessions must be positive")


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
    research: Optional[ResearchConfig] = None
    
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
    research_raw = data.get('research', {})

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

    postgres_cfg = PostgresConfig(
        host=research_raw.get('postgres', {}).get('host', 'localhost'),
        port=research_raw.get('postgres', {}).get('port', 5432),
        database=research_raw.get('postgres', {}).get('database', 'bwired_research'),
        user=research_raw.get('postgres', {}).get('user', 'bwired'),
        password=research_raw.get('postgres', {}).get('password', '')
    )

    searxng_cfg = SearXNGConfig(
        url=research_raw.get('searxng', {}).get('url', 'http://localhost:8080'),
        timeout=research_raw.get('searxng', {}).get('timeout', 30),
        max_results_per_query=research_raw.get('searxng', {}).get('max_results_per_query', 10)
    )

    crawling_cfg = CrawlingConfig(
        max_urls_per_domain=research_raw.get('crawling', {}).get('max_urls_per_domain', 5),
        relevance_threshold=research_raw.get('crawling', {}).get('relevance_threshold', 50),
        timeout=research_raw.get('crawling', {}).get('timeout', 30),
        user_agent=research_raw.get('crawling', {}).get('user_agent', 'BwiredResearchBot/1.0')
    )

    extraction_raw = research_raw.get('extraction', {})
    llm_raw = extraction_raw.get('llm', {})
    ollama_raw = llm_raw.get('ollama', {})
    openai_raw = llm_raw.get('openai', {})

    ollama_llm_cfg = OllamaLLMConfig(
        base_url=ollama_raw.get('base_url', 'http://localhost:11434'),
        model=ollama_raw.get('model', 'llama3.2'),
        timeout=ollama_raw.get('timeout', 120)
    )

    openai_llm_cfg = OpenAILLMConfig(
        api_key=openai_raw.get('api_key', ''),
        model=openai_raw.get('model', 'gpt-4o-mini'),
        base_url=openai_raw.get('base_url'),
        timeout=openai_raw.get('timeout', 120)
    )

    llm_provider_cfg = LLMProviderConfig(
        provider=llm_raw.get('provider', 'ollama'),
        ollama=ollama_llm_cfg,
        openai=openai_llm_cfg
    )

    extraction_cfg = ExtractionConfig(
        batch_size=extraction_raw.get('batch_size', 5),
        confidence_threshold=extraction_raw.get('confidence_threshold', 0.7),
        llm=llm_provider_cfg,
        retrieval_top_k=extraction_raw.get('retrieval_top_k', 10)
    )

    synthesis_raw = research_raw.get('synthesis', {})
    synthesis_llm_raw = synthesis_raw.get('llm', {})
    synthesis_ollama_raw = synthesis_llm_raw.get('ollama', {})
    synthesis_openai_raw = synthesis_llm_raw.get('openai', {})

    synthesis_ollama_llm_cfg = OllamaLLMConfig(
        base_url=synthesis_ollama_raw.get('base_url', 'http://localhost:11434'),
        model=synthesis_ollama_raw.get('model', 'llama3.2'),
        timeout=synthesis_ollama_raw.get('timeout', 180)
    )

    synthesis_openai_llm_cfg = OpenAILLMConfig(
        api_key=synthesis_openai_raw.get('api_key', ''),
        model=synthesis_openai_raw.get('model', 'gpt-4o'),
        base_url=synthesis_openai_raw.get('base_url'),
        timeout=synthesis_openai_raw.get('timeout', 180)
    )

    synthesis_llm_provider_cfg = LLMProviderConfig(
        provider=synthesis_llm_raw.get('provider', 'ollama'),
        ollama=synthesis_ollama_llm_cfg,
        openai=synthesis_openai_llm_cfg
    )

    synthesis_cfg = SynthesisConfig(
        llm=synthesis_llm_provider_cfg,
        max_facts_per_section=synthesis_raw.get('max_facts_per_section', 20),
        min_confidence=synthesis_raw.get('min_confidence', 0.7),
        include_citations=synthesis_raw.get('include_citations', True),
        report_format=synthesis_raw.get('report_format', 'markdown'),
        citation_format=synthesis_raw.get('citation_format', 'url')
    )

    research_cfg = ResearchConfig(
        postgres=postgres_cfg,
        searxng=searxng_cfg,
        crawling=crawling_cfg,
        extraction=extraction_cfg,
        synthesis=synthesis_cfg,
        max_concurrent_sessions=research_raw.get('max_concurrent_sessions', 5)
    )

    return Config(
        chunking=chunking_cfg,
        embedding=embedding_cfg,
        storage=qdrant_cfg,
        reranker=reranker_cfg,
        llm=llm_cfg,
        compression=compression_cfg,
        research=research_cfg
    )