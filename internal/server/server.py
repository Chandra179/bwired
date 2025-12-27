import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from internal.embedding.dense_embedder import DenseEmbedder
from internal.embedding.sparse_embedder import SparseEmbedder
from internal.embedding.reranker import Reranker
from internal.processing.context_compressor import ContextCompressor
from internal.storage.qdrant_client import QdrantClient
from internal.chunkers import ChunkerFactory

from internal.config import (
    load_config,
    Config,
    QdrantConfig,
    RerankerConfig,
    CompressionConfig,
    LLMConfig,
)

from internal.logger import setup_logging

logger = logging.getLogger(__name__)

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class ServerState:
    """Global state container for initialized models and configs"""
    
    def __init__(self):
        self.config: Config = None
        
        self.qdrant_config: QdrantConfig = None
        self.reranker_config: RerankerConfig = None
        self.processor_config: CompressionConfig = None
        self.llm_config: LLMConfig = None
        
        self.dense_embedder: DenseEmbedder = None
        self.sparse_embedder: SparseEmbedder = None
        self.reranker: Reranker = None
        self.processor: ContextCompressor = None
        self.qdrant_client: QdrantClient = None
        self.chunker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting server initialization...")
    
    state = ServerState()
    state.config = load_config("config.yaml") 
    
    state.qdrant_config = state.config.storage
    state.reranker_config = state.config.reranker
    state.llm_config = state.config.llm
    state.processor_config = state.config.compression
    
    try:
        logger.info("Initializing dense embedder...")
        state.dense_embedder = DenseEmbedder(state.config.embedding.dense)
        logger.info("✓ Dense embedder loaded")
    except Exception as e:
        logger.error(f"Failed to load dense embedder: {e}")
        raise
    
    try:
        logger.info("Initializing sparse embedder...")
        state.sparse_embedder = SparseEmbedder(state.config.embedding.sparse)
        logger.info("✓ Sparse embedder loaded")
    except Exception as e:
        logger.error(f"Failed to load sparse embedder: {e}")
        raise
    
    try:
        logger.info("Initializing reranker...")
        state.reranker = Reranker(state.config.reranker)
        logger.info("✓ Reranker loaded")
    except Exception as e:
        logger.error(f"Failed to load reranker: {e}")
        raise
    
    try:
        logger.info("Initializing compressor...")
        state.processor = ContextCompressor(state.config.compression)
        logger.info("✓ Compressor loaded")
    except Exception as e:
        logger.warning(f"Failed to load compressor (optional): {e}")
        state.processor = None
        
    try:
        logger.info("Initializing Qdrant client...")
        state.qdrant_client = QdrantClient(
            config=state.qdrant_config,
            dense_embedding_dim=state.config.embedding.dense.model_dim
        )
        logger.info("✓ Qdrant client initialized and collection ready")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        raise
    
    try:
        logger.info("Initializing chunker...")
        state.chunker = ChunkerFactory.create(format='markdown', config=state.config)
        logger.info("✓ Chunker loaded")
    except Exception as e:
        logger.error(f"Failed to load chunker: {e}")
        raise
    
    app.state.server_state = state
    
    logger.info("="*60)
    logger.info("✓ Server initialization complete!")
    logger.info("="*60)
    
    yield
    
    logger.info("Shutting down server...")


app = FastAPI(
    title="Document Search API",
    description="RAG-based document search with PDF processing",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from .search_api import router as search_router
from .upload_docs_api import router as upload_router
app.include_router(search_router)
app.include_router(upload_router)


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
    state = app.state.server_state
    return {
        "status": "healthy",
        "models": {
            "dense_embedder": "loaded" if state.dense_embedder else "failed",
            "sparse_embedder": "loaded" if state.sparse_embedder else "failed",
            "reranker": "loaded" if state.reranker else "failed",
            "qdrant_client": "connected" if state.qdrant_client else "failed"
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