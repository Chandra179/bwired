from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ChunkingConfig:
    """Default configuration for semantic chunking, Custom config at .yaml files"""
    
    # Size parameters (in tokens)
    target_chunk_size: int = 500
    min_chunk_size: int = 100
    max_chunk_size: int = 800
    
    # Semantic chunking behavior
    keep_tables_intact: bool = True
    keep_code_blocks_intact: bool = True
    keep_list_items_together: bool = True
    
    # Sentence boundaries
    use_sentence_boundaries: bool = True
    never_split_mid_sentence: bool = True
    
    # Recursion control
    max_recursion_depth: int = 3
    
    def __post_init__(self):
        """Validate configuration"""
        if self.min_chunk_size > self.target_chunk_size:
            raise ValueError(
                f"min_chunk_size ({self.min_chunk_size}) must be <= "
                f"target_chunk_size ({self.target_chunk_size})"
            )
        if self.target_chunk_size > self.max_chunk_size:
            raise ValueError(
                f"target_chunk_size ({self.target_chunk_size}) must be <= "
                f"max_chunk_size ({self.max_chunk_size})"
            )


@dataclass
class ContextConfig:
    """Configuration for context enhancement"""
    
    # Document-level context
    include_document_context: bool = True
    
    # Hierarchical context
    include_header_path: bool = True
    include_section_summary: bool = False  # Future: LLM-generated
    
    # Local context
    include_surrounding_context: bool = True
    surrounding_sentences_before: int = 2
    surrounding_sentences_after: int = 1
    
    # Entity extraction
    extract_entities: bool = True
    entity_types: List[str] = field(default_factory=lambda: [
        "PERSON", "ORG", "PRODUCT", "GPE", "DATE", "MONEY"
    ])
    
    # Multi-representation
    create_table_descriptions: bool = True
    create_code_descriptions: bool = True


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
    
    # Batch processing
    batch_size: int = 32


@dataclass
class RAGChunkingConfig:
    """Complete RAG chunking configuration"""
    
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    
    def __post_init__(self):
        """Cross-validate configurations"""
        if self.chunking.max_chunk_size > self.embedding.max_token_limit:
            raise ValueError(
                f"chunking.max_chunk_size ({self.chunking.max_chunk_size}) must be <= "
                f"embedding.max_token_limit ({self.embedding.max_token_limit})"
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