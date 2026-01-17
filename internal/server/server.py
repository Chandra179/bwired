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
from internal.storage.postgres_client import PostgresClient, PostgresConfig
from internal.research.template_manager import TemplateManager
from internal.research.synthesizer import ResearchSynthesizer
from internal.research.research_pipeline import ResearchPipeline
from internal.server import research_api
from internal.server import template_api
from internal.chunkers import ChunkerFactory, BaseDocumentChunker

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
        self.config: Optional[Config] = None

        self.qdrant_config: Optional[QdrantConfig] = None
        self.reranker_config: Optional[RerankerConfig] = None
        self.processor_config: Optional[CompressionConfig] = None
        self.llm_config: Optional[LLMConfig] = None

        self.dense_embedder: Optional[DenseEmbedder] = None
        self.sparse_embedder: Optional[SparseEmbedder] = None
        self.reranker: Optional[Reranker] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self.postgres_client: Optional[PostgresClient] = None
        self.template_manager: Optional[TemplateManager] = None
        self.chunker: Optional[BaseDocumentChunker] = None
        self.research_pipeline: Optional[ResearchPipeline] = None
        self.synthesizer: Optional[ResearchSynthesizer] = None


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
        if state.config.reranker:
            state.reranker = Reranker(state.config.reranker)
            logger.info("✓ Reranker loaded")
    except Exception as e:
        logger.error(f"Failed to load reranker: {e}")
        raise

    try:
        logger.info("Initializing Qdrant client...")
        if state.qdrant_config:
            state.qdrant_client = QdrantClient(
                config=state.qdrant_config,
                dense_embedding_dim=state.config.embedding.dense.model_dim,
            )
            logger.info("✓ Qdrant client initialized and collection ready")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        raise

    try:
        logger.info("Initializing chunker...")
        state.chunker = ChunkerFactory.create(format="markdown", config=state.config)
        logger.info("✓ Chunker loaded")
    except Exception as e:
        logger.error(f"Failed to load chunker: {e}")
        raise

    try:
        logger.info("Initializing PostgreSQL client...")
        if state.config.research:
            pg_config = PostgresConfig(
                host=state.config.research.postgres.host,
                port=state.config.research.postgres.port,
                database=state.config.research.postgres.database,
                user=state.config.research.postgres.user,
                password=state.config.research.postgres.password,
            )
            state.postgres_client = PostgresClient(pg_config)

            logger.info("Initializing template manager...")
            state.template_manager = TemplateManager(state.postgres_client)
            logger.info("✓ Template manager loaded")

            logger.info("Initializing research synthesizer...")
            from internal.llm import create_llm_client

            state.synthesizer = ResearchSynthesizer(
                postgres_client=state.postgres_client,
                llm_client=create_llm_client(state.config.research.synthesis.llm),
                config=state.config.research.synthesis,
            )
            logger.info("✓ Research synthesizer loaded")

            logger.info("Initializing research pipeline...")
            if state.qdrant_client is None:
                logger.warning(
                    "Qdrant client not available, skipping research pipeline"
                )
            else:
                state.research_pipeline = ResearchPipeline(
                    config=state.config,
                    postgres_client=state.postgres_client,
                    qdrant_client=state.qdrant_client,
                    chunker=state.chunker,
                    dense_embedder=state.dense_embedder,
                    sparse_embedder=state.sparse_embedder,
                    reranker=state.reranker,
                    synthesizer=state.synthesizer,
                )
                logger.info("✓ Research pipeline loaded")
        else:
            logger.warning(
                "Research config not found, skipping PostgreSQL and template manager"
            )
    except Exception as e:
        logger.error(f"Failed to initialize research components: {e}")
        raise

    app.state.server_state = state

    logger.info("=" * 60)
    logger.info("✓ Server initialization complete!")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down server...")


app = FastAPI(
    title="Document Search API",
    description="RAG-based document search with agentic AI",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(research_api.router, prefix="/api")

app.include_router(template_api.router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Document Search API is running",
        "version": "2.0.0 (Agentic)",
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    state: ServerState = app.state.server_state
    return {
        "status": "healthy",
        "models": {
            "dense_embedder": "loaded" if state.dense_embedder else "failed",
            "sparse_embedder": "loaded" if state.sparse_embedder else "failed",
            "reranker": "loaded" if state.reranker else "failed",
            "qdrant_client": "connected" if state.qdrant_client else "failed",
        },
    }


if __name__ == "__main__":
    import uvicorn

    setup_logging("INFO")

    uvicorn.run(
        "server.server:app", host="0.0.0.0", port=8000, reload=False, log_level="info"
    )
