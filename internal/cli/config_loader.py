import yaml
from typing import Tuple, Dict, Any, Optional
import logging

from ..config import (
    EmbeddingConfig,
    DenseEmbeddingConfig,
    SparseEmbeddingConfig,
    RerankerConfig,
    QdrantConfig,
    ProcessorConfig,
    CompressionConfig
)

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """Loads and validates configuration from YAML files"""
    
    def load_search_config(
        self, 
        config_path: str
    ) -> Tuple[EmbeddingConfig, RerankerConfig, QdrantConfig, Dict[str, Any], str, Optional[ProcessorConfig]]:
        """
        Load search configuration from YAML file
        
        Args:
            config_path: Path to search.yaml configuration file
            
        Returns:
            Tuple of (embedding_config, reranker_config, qdrant_config, search_params, log_level, processor_config)
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
        
        return embedding_config, reranker_config, qdrant_config, search_params, log_level, processor_config