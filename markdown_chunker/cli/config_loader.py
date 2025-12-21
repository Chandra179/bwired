import logging
from typing import Tuple
from pathlib import Path
import yaml

from ..config import (
    RAGChunkingConfig, 
    ChunkingConfig, 
    ContextConfig, 
    EmbeddingConfig,    
    QdrantConfig
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
        
        embedding_token_limit = config_data.get('embedding_token_limit', 512  )
        chunk_size = config_data.get('chunk_size', 400)
        
        chunking_config = ChunkingConfig(
            chunk_size=chunk_size,
            overlap_tokens=config_data.get('overlap_tokens', 0),
            use_sentence_boundaries=config_data.get('use_sentence_boundaries', True),
        )
        
        context_config = ContextConfig(
            include_header_path=config_data.get('include_header_path', True),
        )
        
        embedding_config = EmbeddingConfig(
            dense_model_name=config_data.get('dense_model_name', 'BAAI/bge-base-en-v1.5'),
            sparse_model_name=config_data.get('sparse_model_name', 'prithivida/Splade_PP_en_v1'),
            reranker_model_name=config_data.get('reranker_model_name', 'BAAI/bge-reranker-v2-m3'),
            model_dim=config_data.get('model_dim', 768),
            embedding_token_limit=embedding_token_limit,
            device=config_data.get('device', 'cpu'),
            batch_size=config_data.get('embedding_batch_size', 128),
            use_fp16=config_data.get('use_fp16', True),
            show_progress_bar=config_data.get('show_progress_bar', False)
        )
        
        rag_config = RAGChunkingConfig(
            chunking=chunking_config,
            context=context_config,
            embedding=embedding_config
        )
        
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
    def load_search_config(config_path: str) -> Tuple[EmbeddingConfig, QdrantConfig, dict, str]:
        """
        Load configuration for search command
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Tuple of (EmbeddingConfig, QdrantConfig, search_params, log_level)
        """
        logger.info(f"Loading search config from: {config_path}")
        config_data = load_config_file(config_path)
        
        embedding_token_limit = config_data.get('embedding_token_limit', 512)
        
        embedding_config = EmbeddingConfig(
            dense_model_name=config_data.get('model_name', 'BAAI/bge-base-en-v1.5'),
            embedding_token_limit=embedding_token_limit,
            device=config_data.get('device', 'cpu')
        )
        
        qdrant_config = QdrantConfig(
            url=config_data.get('qdrant_url', 'http://localhost:6333'),
            collection_name=config_data.get('collection_name', 'markdown_chunks'),
        )
        
        search_params = {
            'limit': config_data.get('search_limit', 5),
            'score_threshold': config_data.get('score_threshold'),
        }
        
        log_level = config_data.get('log_level', 'INFO')
        
        return embedding_config, qdrant_config, search_params, log_level


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