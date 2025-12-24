import logging
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
import yaml

from ..config import (
    RAGChunkingConfig,
    ChunkingConfig,
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
        Load configuration for vectorize command using the new dataclass structure
        """
        logger.info(f"Loading vectorize config from: {config_path}")
        config_data = load_config_file(config_path)
        
        chunking_cfg = ChunkingConfig(
            max_chunk_size=config_data.get('max_chunk_size', 512),
            overlap_tokens=config_data.get('overlap_tokens', 50),
            include_section_path=config_data.get('include_section_path', True)
        )
        
        dense_cfg = DenseEmbeddingConfig(
            model_name=config_data.get('dense_model_name', 'BAAI/bge-base-en-v1.5'),
            device=config_data.get('device', 'cpu'),
            batch_size=config_data.get('embedding_batch_size', 128),
            use_fp16=config_data.get('use_fp16', True),
            show_progress_bar=config_data.get('show_progress_bar', False),
            model_dim=config_data.get('model_dim', 768)
        )
        
        sparse_cfg = SparseEmbeddingConfig(
            model_name=config_data.get('sparse_model_name', 'prithivida/Splade_PP_en_v1'),
            batch_size=config_data.get('sparse_batch_size', 8),
            threads=config_data.get('sparse_threads', 4)
        )
        
        embedding_cfg = EmbeddingConfig(
            dense=dense_cfg,
            sparse=sparse_cfg,
            embedding_token_limit=config_data.get('embedding_token_limit', 512)
        )
        
        qdrant_cfg = QdrantConfig(
            url=config_data.get('qdrant_url', 'http://localhost:6333'),
            collection_name=config_data.get('collection_name', 'markdown_chunks'),
            distance_metric=config_data.get('distance_metric', 'Cosine'),
            grpc_port=config_data.get('grpc_port', 6334),
            storage_batch_size=config_data.get('storage_batch_size', 500)
        )
        
        rag_config = RAGChunkingConfig(
            chunking=chunking_cfg,
            embedding=embedding_cfg,
            storage=qdrant_cfg
        )
        
        log_level = config_data.get('log_level', 'INFO')
        
        return rag_config, qdrant_cfg, log_level
    
    
    @staticmethod
    def load_search_config(
        config_path: str
    ) -> Tuple[EmbeddingConfig, RerankerConfig, QdrantConfig, Dict[str, Any], str, Optional[ProcessorConfig], LLMConfig]:
        """
        Load search configuration from YAML file mapped to new dataclasses
        """
        config = load_config_file(config_path)
        
        # Load embedding config
        emb_section = config.get('embedding', {})
        dense_sec = emb_section.get('dense', {})
        sparse_sec = emb_section.get('sparse', {})
        
        embedding_config = EmbeddingConfig(
            dense=DenseEmbeddingConfig(
                model_name=dense_sec.get('model_name', 'BAAI/bge-base-en-v1.5'),
                device=dense_sec.get('device', 'cpu'),
                batch_size=dense_sec.get('batch_size', 32),
                use_fp16=dense_sec.get('use_fp16', False),
                show_progress_bar=dense_sec.get('show_progress_bar', True),
                model_dim=emb_section.get('model_dim', 768)
            ),
            sparse=SparseEmbeddingConfig(
                model_name=sparse_sec.get('model_name', 'prithivida/Splade_PP_en_v1'),
                batch_size=sparse_sec.get('batch_size', 8),
                threads=sparse_sec.get('threads', 4)
            ),
            embedding_token_limit=emb_section.get('embedding_token_limit', 512)
        )
        
        # Load reranker config
        rerank_sec = config.get('reranker', {})
        reranker_config = RerankerConfig(
            model_name=rerank_sec.get('model_name', 'BAAI/bge-reranker-v2-m3'),
            device=rerank_sec.get('device', 'cpu'),
            batch_size=rerank_sec.get('batch_size', 32),
            enabled=rerank_sec.get('enabled', False)
        )
        
        # Load Qdrant config
        qdrant_sec = config.get('qdrant', {})
        qdrant_config = QdrantConfig(
            url=qdrant_sec.get('url', 'http://localhost:6333'),
            collection_name=qdrant_sec.get('collection_name', 'markdown_chunks'),
            distance_metric=qdrant_sec.get('distance_metric', 'Cosine'),
            grpc_port=qdrant_sec.get('grpc_port', 6334),
            storage_batch_size=qdrant_sec.get('storage_batch_size', 100)
        )
        
        # Processor / Compression
        proc_sec = config.get('processor', {})
        processor_config = None
        if proc_sec:
            comp_sec = proc_sec.get('compression')
            compression_config = None
            if comp_sec:
                compression_config = CompressionConfig(
                    model_name=comp_sec.get('model_name', 'microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank'),
                    compression_ratio=comp_sec.get('compression_ratio'),
                    token_limit=comp_sec.get('token_limit'),
                    device=comp_sec.get('device', 'cpu')
                )
            processor_config = ProcessorConfig(
                enabled=proc_sec.get('enabled', False),
                compression=compression_config
            )
        
        # LLM config
        llm_sec = config.get('llm', {})
        llm_config = LLMConfig(
            model=llm_sec.get('model', 'llama3.2'),
            temperature=llm_sec.get('temperature', 0.1),
            system_prompt_path=llm_sec.get('system_prompt_path', 'prompts/system_prompt.j2'),
            user_prompt_path=llm_sec.get('user_prompt_path', 'prompts/user_prompt.j2'),
            max_tokens=llm_sec.get('max_tokens', 1000)
        )
        
        search_params = {'limit': config.get('search', {}).get('limit', 10)}
        log_level = config.get('logging', {}).get('level', 'INFO')
        
        return embedding_config, reranker_config, qdrant_config, search_params, log_level, processor_config, llm_config


def load_config_file(config_path: str) -> dict:
    """Helper to read YAML from path"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config or {}