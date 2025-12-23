import logging
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
import yaml

from ..config import (
    RAGChunkingConfig,
    ChunkingConfig,
    ContextConfig,
    EmbeddingConfig,
    DenseEmbeddingConfig,
    SparseEmbeddingConfig,
    ProcessorConfig,
    RerankerConfig,
    QdrantConfig,
    CompressionConfig,
    LLMConfig
)

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """Load and parse configuration files for different commands"""
    
    @staticmethod
    def load_vectorize_config(config_path: str) -> Tuple[RAGChunkingConfig, QdrantConfig, str]:
        """
        Load configuration for vectorize command
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Tuple of (RAGChunkingConfig, QdrantConfig, log_level)
        """
        logger.info(f"Loading vectorize config from: {config_path}")
        config_data = load_config_file(config_path)
        
        # Chunking configuration
        chunking_config = ChunkingConfig(
            chunk_size=config_data.get('chunk_size', 400),
            overlap_tokens=config_data.get('overlap_tokens', 0),
            use_sentence_boundaries=config_data.get('use_sentence_boundaries', True),
        )
        
        # Context configuration
        context_config = ContextConfig(
            include_header_path=config_data.get('include_header_path', True),
        )
        
        # Dense embedding configuration
        dense_config = DenseEmbeddingConfig(
            model_name=config_data.get('dense_model_name', 'BAAI/bge-base-en-v1.5'),
            device=config_data.get('device', 'cpu'),
            batch_size=config_data.get('embedding_batch_size', 128),
            use_fp16=config_data.get('use_fp16', True),
            show_progress_bar=config_data.get('show_progress_bar', False)
        )
        
        # Sparse embedding configuration
        sparse_config = SparseEmbeddingConfig(
            model_name=config_data.get('sparse_model_name', 'prithivida/Splade_PP_en_v1'),
            batch_size=config_data.get('sparse_batch_size', 8),
            threads=config_data.get('sparse_threads', 4)
        )
        
        # Combined embedding configuration
        embedding_config = EmbeddingConfig(
            dense=dense_config,
            sparse=sparse_config,
            embedding_token_limit=config_data.get('embedding_token_limit', 512),
            model_dim=config_data.get('model_dim', 768)
        )
        
        # RAG configuration
        rag_config = RAGChunkingConfig(
            chunking=chunking_config,
            context=context_config,
            embedding=embedding_config
        )
        
        # Qdrant configuration
        qdrant_config = QdrantConfig(
            url=config_data.get('qdrant_url', 'http://localhost:6333'),
            collection_name=config_data.get('collection_name', 'markdown_chunks'),
            distance_metric=config_data.get('distance_metric', 'Cosine'),
            grpc_port=config_data.get('grpc_port', 6334),
            storage_batch_size=config_data.get('storage_batch_size', 500)
        )
        
        log_level = config_data.get('log_level', 'INFO')
        
        return rag_config, qdrant_config, log_level
    
    @staticmethod
    def load_search_config(
        config_path: str
    ) -> Tuple[EmbeddingConfig, RerankerConfig, QdrantConfig, Dict[str, Any], str, Optional[ProcessorConfig], LLMConfig]:
        """
        Load search configuration from YAML file
        
        Args:
            config_path: Path to search.yaml configuration file
            
        Returns:
            Tuple of (embedding_config, reranker_config, qdrant_config, search_params, log_level, processor_config, llm_config)
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Load embedding config
        embedding_cfg = config.get('embedding', {})
        dense_cfg = embedding_cfg.get('dense', {})
        sparse_cfg = embedding_cfg.get('sparse', {})
        
        embedding_config = EmbeddingConfig(
            dense=DenseEmbeddingConfig(
                model_name=dense_cfg.get('model_name', 'BAAI/bge-base-en-v1.5'),
                device=dense_cfg.get('device', 'cpu'),
                batch_size=dense_cfg.get('batch_size', 32),
                use_fp16=dense_cfg.get('use_fp16', False),
                show_progress_bar=dense_cfg.get('show_progress_bar', True)
            ),
            sparse=SparseEmbeddingConfig(
                model_name=sparse_cfg.get('model_name', 'prithivida/Splade_PP_en_v1'),
                batch_size=sparse_cfg.get('batch_size', 8),
                threads=sparse_cfg.get('threads', 4)
            ),
            embedding_token_limit=embedding_cfg.get('embedding_token_limit', 512),
            model_dim=embedding_cfg.get('model_dim', 768)
        )
        
        # Load reranker config
        reranker_cfg = config.get('reranker', {})
        reranker_config = RerankerConfig(
            model_name=reranker_cfg.get('model_name', 'BAAI/bge-reranker-v2-m3'),
            device=reranker_cfg.get('device', 'cpu'),
            batch_size=reranker_cfg.get('batch_size', 32)
        )
        
        # Load Qdrant config
        qdrant_cfg = config.get('qdrant', {})
        qdrant_config = QdrantConfig(
            url=qdrant_cfg.get('url', 'http://localhost:6333'),
            collection_name=qdrant_cfg.get('collection_name', 'markdown_chunks'),
            distance_metric=qdrant_cfg.get('distance_metric', 'Cosine'),
            grpc_port=qdrant_cfg.get('grpc_port', 6334),
            storage_batch_size=qdrant_cfg.get('storage_batch_size', 100)
        )
        
        # Load search parameters
        search_params = {
            'limit': config.get('search', {}).get('limit', 10)
        }
        
        # Load log level
        log_level = config.get('logging', {}).get('level', 'INFO')
        
        # Load processor config (optional)
        processor_config = None
        processor_cfg = config.get('processor')
        if processor_cfg:
            enabled = processor_cfg.get('enabled', False)
            compression_cfg = processor_cfg.get('compression')
            
            compression_config = None
            if compression_cfg:
                compression_config = CompressionConfig(
                    model_name=compression_cfg.get(
                        'model_name', 
                        'microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank'
                    ),
                    compression_ratio=compression_cfg.get('compression_ratio'),
                    token_limit=compression_cfg.get('token_limit'),
                    device=compression_cfg.get('device', 'cpu')
                )
            
            processor_config = ProcessorConfig(
                enabled=enabled,
                compression=compression_config
            )
            
            logger.info(f"Processor config loaded: enabled={enabled}")
        else:
            logger.info("No processor configuration found")
        
        # Load LLM config
        llm_cfg = config.get('llm', {})
        llm_config = LLMConfig(
            model=llm_cfg.get('model', 'llama3.2'),
            temperature=llm_cfg.get('temperature', 0.1),
            system_prompt_path=llm_cfg.get('system_prompt_path', 'prompts/system_prompt.j2'),
            user_prompt_path=llm_cfg.get('user_prompt_path', 'prompts/user_prompt.j2'),
            max_tokens=llm_cfg.get('max_tokens', 1000)
        )
        
        logger.info(f"LLM config loaded: model={llm_config.model}")
        
        return embedding_config, reranker_config, qdrant_config, search_params, log_level, processor_config, llm_config


def load_config_file(config_path: str) -> dict:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config or {}