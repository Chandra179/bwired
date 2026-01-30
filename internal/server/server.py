import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from internal.embedding.dense_embedder import DenseEmbedder
from internal.embedding.sparse_embedder import SparseEmbedder
from internal.processing.reranker import Reranker
from internal.storage.qdrant_client import QdrantClient
from internal.chunkers import ChunkerFactory, BaseDocumentChunker
from internal.retriever.retriever import Retriever
from internal.processing.document_processor import DocumentProcessor
from internal.searxng.client import SearXNGClient

from internal.config import (
    load_config,
    Config,
    QdrantConfig,
    RerankerConfig,
    CompressionConfig,
    LLMConfig,
    SearXNGConfig,
)

from internal.logger import setup_logging

# Import endpoint modules from internal.api
from internal.api import (
    health_router,
    documents_router,
    search_router,
    web_search_router,
)

logger = logging.getLogger(__name__)

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class ServerState:
    """Global state container for initialized models and configs"""
    
    def __init__(self):
        self.config: Optional[Config] = None
        
        self.qdrant_config: Optional[QdrantConfig] = None
        self.reranker_config: Optional[RerankerConfig] = None
        self.processor_config: Optional[CompressionConfig] = None
        self.llm_config: Optional[LLMConfig] = None
        self.searxng_config: Optional[SearXNGConfig] = None
        
        self.dense_embedder: Optional[DenseEmbedder] = None
        self.sparse_embedder: Optional[SparseEmbedder] = None
        self.reranker: Optional[Reranker] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self.chunker: Optional[BaseDocumentChunker] = None
        self.retriever: Optional[Retriever] = None
        self.document_processor: Optional[DocumentProcessor] = None
        self.searxng_client: Optional[SearXNGClient] = None


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
    state.searxng_config = state.config.searxng
    
    # try:
    #     logger.info("Initializing dense embedder...")
    #     state.dense_embedder = DenseEmbedder(state.config.embedding.dense)
    #     logger.info("✓ Dense embedder loaded")
    # except Exception as e:
    #     logger.error(f"Failed to load dense embedder: {e}")
    #     raise
    
    # try:
    #     logger.info("Initializing sparse embedder...")
    #     state.sparse_embedder = SparseEmbedder(state.config.embedding.sparse)
    #     logger.info("✓ Sparse embedder loaded")
    # except Exception as e:
    #     logger.error(f"Failed to load sparse embedder: {e}")
    #     raise
    
    # try:
    #     logger.info("Initializing reranker...")
    #     if state.config.reranker:
    #         state.reranker = Reranker(state.config.reranker)
    #         logger.info("✓ Reranker loaded")
    # except Exception as e:
    #     logger.error(f"Failed to load reranker: {e}")
    #     raise
        
    # try:
    #     logger.info("Initializing Qdrant client...")
    #     if state.qdrant_config:
    #         state.qdrant_client = QdrantClient(
    #             config=state.qdrant_config,
    #             dense_embedding_dim=state.config.embedding.dense.model_dim
    #         )
    #         logger.info("✓ Qdrant client initialized and collection ready")
    # except Exception as e:
    #     logger.error(f"Failed to initialize Qdrant client: {e}")
    #     raise
    
    # try:
    #     logger.info("Initializing retriever...")
    #     if state.qdrant_client and state.reranker:
    #         state.retriever = Retriever(
    #             qdrant_client=state.qdrant_client,
    #             reranker=state.reranker,
    #             llm_config=state.llm_config,
    #             processor=None
    #         )
    #         logger.info("✓ Retriever initialized")
    # except Exception as e:
    #     logger.error(f"Failed to initialize retriever: {e}")
    #     raise
    
    # try:
    #     logger.info("Initializing chunker...")
    #     state.chunker = ChunkerFactory.create(format='markdown', config=state.config)
    #     logger.info("✓ Chunker loaded")
    # except Exception as e:
    #     logger.error(f"Failed to load chunker: {e}")
    #     raise
    
    # try:
    #     logger.info("Initializing document processor...")
    #     assert state.qdrant_client is not None
    #     state.document_processor = DocumentProcessor(
    #         chunker=state.chunker,
    #         dense_embedder=state.dense_embedder,
    #         sparse_embedder=state.sparse_embedder,
    #         qdrant_client=state.qdrant_client
    #     )
    #     logger.info("✓ Document processor loaded")
    # except Exception as e:
    #     logger.error(f"Failed to load document processor: {e}")
    #     raise
    
    try:
        logger.info("Initializing SearXNG client...")
        if state.searxng_config:
            state.searxng_client = SearXNGClient(state.searxng_config)
            logger.info("✓ SearXNG client loaded")
        else:
            logger.warning("SearXNG configuration not found, skipping SearXNG client initialization")
    except Exception as e:
        logger.error(f"Failed to load SearXNG client: {e}")
        raise
    
    app.state.server_state = state
    
    logger.info("="*60)
    logger.info("✓ Server initialization complete!")
    logger.info("="*60)
    
    yield
    
    logger.info("Shutting down server...")


app = FastAPI(
    title="Document Search API",
    description="RAG-based document search with agentic AI",
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include endpoint routers
app.include_router(health_router, tags=["health"])
app.include_router(documents_router, tags=["documents"])
app.include_router(search_router, tags=["search"])
app.include_router(web_search_router, tags=["web-search"])


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