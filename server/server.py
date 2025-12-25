import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yaml

from internal.embedding.dense_embedder import DenseEmbedder
from internal.embedding.sparse_embedder import SparseEmbedder
from internal.embedding.reranker import Reranker
from internal.generator.engine import LocalEngine
from internal.processing.compressor import LLMLinguaCompressor
from internal.config import (
    RAGChunkingConfig, ChunkingConfig, EmbeddingConfig, 
    DenseEmbeddingConfig, SparseEmbeddingConfig, 
    QdrantConfig, RerankerConfig, ProcessorConfig, LLMConfig
)
from internal.logger import setup_logging

logger = logging.getLogger(__name__)

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class ServerState:
    """Global state container for initialized models and configs"""
    
    def __init__(self):
        # Configs
        self.rag_config: RAGChunkingConfig = None
        self.qdrant_config: QdrantConfig = None
        self.reranker_config: RerankerConfig = None
        self.processor_config: ProcessorConfig = None
        self.llm_config: LLMConfig = None
        
        # Models and clients
        self.dense_embedder: DenseEmbedder = None
        self.sparse_embedder: SparseEmbedder = None
        self.reranker: Reranker = None
        self.llm_engine: LocalEngine = None
        self.processor: LLMLinguaCompressor = None


def load_vectorize_config(config_path: str = "vectorize.yaml") -> tuple:
    """Load vectorize configuration from YAML"""
    logger.info(f"Loading vectorize config from: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f) or {}
    
    chunking_cfg = ChunkingConfig(
        max_chunk_size=config_data.get('chunk_size', 512),
        overlap_tokens=config_data.get('overlap_tokens', 50),
        include_section_path=config_data.get('include_header_path', True)
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
    
    return rag_config, qdrant_cfg


def load_search_config(config_path: str = "search.yaml") -> tuple:
    """Load search configuration from YAML"""
    logger.info(f"Loading search config from: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
    
    # Embedding config
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
    
    # Reranker config
    rerank_sec = config.get('reranker', {})
    reranker_config = RerankerConfig(
        model_name=rerank_sec.get('model_name', 'BAAI/bge-reranker-v2-m3'),
        device=rerank_sec.get('device', 'cpu'),
        batch_size=rerank_sec.get('batch_size', 32),
        enabled=rerank_sec.get('enabled', True)
    )
    
    # Qdrant config
    qdrant_sec = config.get('qdrant', {})
    qdrant_config = QdrantConfig(
        url=qdrant_sec.get('url', 'http://localhost:6333'),
        collection_name=qdrant_sec.get('collection_name', 'markdown_chunks'),
        distance_metric=qdrant_sec.get('distance_metric', 'Cosine'),
        grpc_port=qdrant_sec.get('grpc_port', 6334),
        storage_batch_size=qdrant_sec.get('storage_batch_size', 100)
    )
    
    # Processor config
    proc_sec = config.get('processor', {})
    processor_config = None
    if proc_sec and proc_sec.get('enabled', False):
        from internal.config import CompressionConfig
        comp_sec = proc_sec.get('compression', {})
        compression_config = CompressionConfig(
            model_name=comp_sec.get('model_name', 'microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank'),
            compression_ratio=comp_sec.get('compression_ratio'),
            token_limit=comp_sec.get('token_limit'),
            device=comp_sec.get('device', 'cpu')
        )
        processor_config = ProcessorConfig(
            enabled=True,
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
    
    return embedding_config, reranker_config, qdrant_config, processor_config, llm_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting server initialization...")
    
    # Load configurations
    rag_config, qdrant_config = load_vectorize_config("vectorize.yaml")
    embedding_config, reranker_config, qdrant_config_search, processor_config, llm_config = load_search_config("search.yaml")
    
    # Store configs in state
    state = ServerState()
    state.rag_config = rag_config
    state.qdrant_config = qdrant_config
    state.reranker_config = reranker_config
    state.processor_config = processor_config
    state.llm_config = llm_config
    
    # Initialize models with error handling
    try:
        logger.info("Initializing dense embedder...")
        state.dense_embedder = DenseEmbedder(rag_config.embedding.dense)
        logger.info("✓ Dense embedder loaded")
    except Exception as e:
        logger.error(f"Failed to load dense embedder: {e}")
        raise
    
    try:
        logger.info("Initializing sparse embedder (this may download models on first run)...")
        state.sparse_embedder = SparseEmbedder(rag_config.embedding.sparse)
        logger.info("✓ Sparse embedder loaded")
    except Exception as e:
        logger.error(f"Failed to load sparse embedder: {e}")
        logger.error("If this is the first run, the model needs to download. Please wait...")
        raise
    
    try:
        logger.info("Initializing reranker...")
        state.reranker = Reranker(reranker_config)
        logger.info("✓ Reranker loaded")
    except Exception as e:
        logger.error(f"Failed to load reranker: {e}")
        raise
    
    try:
        logger.info("Initializing LLM engine...")
        state.llm_engine = LocalEngine(model=llm_config.model)
        logger.info("✓ LLM engine loaded")
    except Exception as e:
        logger.error(f"Failed to load LLM engine: {e}")
        logger.error("Make sure Ollama is running and the model is available")
        raise
    
    if processor_config and processor_config.enabled:
        try:
            logger.info("Initializing compressor...")
            state.processor = LLMLinguaCompressor(processor_config)
            logger.info("✓ Compressor loaded")
        except Exception as e:
            logger.warning(f"Failed to load compressor (optional): {e}")
            state.processor = None
    
    app.state.server_state = state
    
    logger.info("="*60)
    logger.info("✓ Server initialization complete!")
    logger.info("="*60)
    
    yield
    
    logger.info("Shutting down server...")


# Create FastAPI app
app = FastAPI(
    title="Document Search API",
    description="RAG-based document search with PDF processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from .search_api import router as search_router
app.include_router(search_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Document Search API is running"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "models": {
            "dense_embedder": "loaded",
            "sparse_embedder": "loaded",
            "reranker": "loaded",
            "llm_engine": "loaded"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    setup_logging("INFO")
    
    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )