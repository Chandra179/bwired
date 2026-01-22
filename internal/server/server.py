import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
import numpy as np
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from internal.embedding.dense_embedder import DenseEmbedder
from internal.embedding.sparse_embedder import SparseEmbedder
from internal.processing.reranker import Reranker
from internal.storage.qdrant_client import QdrantClient
from internal.chunkers import ChunkerFactory, BaseDocumentChunker
from internal.retriever.retriever import Retriever
from internal.processing.document_extractor import convert_pdf_to_markdown
from internal.processing.document_processor import DocumentProcessor

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
        self.chunker: Optional[BaseDocumentChunker] = None
        self.retriever: Optional[Retriever] = None
        self.document_processor: Optional[DocumentProcessor] = None


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
                dense_embedding_dim=state.config.embedding.dense.model_dim
            )
            logger.info("✓ Qdrant client initialized and collection ready")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        raise
    
    try:
        logger.info("Initializing retriever...")
        if state.qdrant_client and state.reranker:
            state.retriever = Retriever(
                qdrant_client=state.qdrant_client,
                reranker=state.reranker,
                llm_config=state.llm_config,
                processor=None
            )
            logger.info("✓ Retriever initialized")
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        raise
    
    try:
        logger.info("Initializing chunker...")
        state.chunker = ChunkerFactory.create(format='markdown', config=state.config)
        logger.info("✓ Chunker loaded")
    except Exception as e:
        logger.error(f"Failed to load chunker: {e}")
        raise
    
    try:
        logger.info("Initializing document processor...")
        assert state.qdrant_client is not None
        state.document_processor = DocumentProcessor(
            chunker=state.chunker,
            dense_embedder=state.dense_embedder,
            sparse_embedder=state.sparse_embedder,
            qdrant_client=state.qdrant_client
        )
        logger.info("✓ Document processor loaded")
    except Exception as e:
        logger.error(f"Failed to load document processor: {e}")
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


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Document Search API is running",
        "version": "2.1.0"
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
            "retriever": "loaded" if state.retriever else "failed",
            "document_processor": "loaded" if state.document_processor else "failed"
        }
    }


@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    """
    Convert uploaded PDF to markdown using Docling
    
    Args:
        file: PDF file to convert
        
    Returns:
        JSON with converted markdown content
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / file.filename
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        markdown_content = convert_pdf_to_markdown(temp_path)
        
        return {
            "filename": file.filename,
            "markdown": markdown_content,
            "char_count": len(markdown_content)
        }
    except Exception as e:
        logger.error(f"Failed to extract PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract PDF: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/process-markdown-file")
async def process_markdown_file(
    file: UploadFile = File(...),
    collection_name: str = "documents"
):
    """
    Upload markdown file, chunk, embed, and store in Qdrant
    
    Creates a new collection for each document. Returns error if collection
    already exists.
    
    Args:
        file: Uploaded .md file
        collection_name: Target Qdrant collection name
        
    Returns:
        Simple success/failure response with document_id
    """
    if not file.filename or not file.filename.lower().endswith('.md'):
        raise HTTPException(
            status_code=400,
            detail="File must be a markdown file (.md)"
        )
    
    try:
        markdown_content = await file.read()
        markdown_text = markdown_content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Failed to decode markdown file (must be UTF-8)"
        )
    
    state: ServerState = app.state.server_state
    if not state.document_processor:
        raise HTTPException(
            status_code=503,
            detail="Document processor not initialized"
        )
    
    try:
        result = await state.document_processor.process_markdown_file(
            markdown_content=markdown_text,
            collection_name=collection_name
        )
        return result
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(
                status_code=409,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Failed to process markdown file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process markdown file: {str(e)}"
        )


class SearchRequest(BaseModel):
    query: str
    collection_name: str = "documents"
    limit: int = 10


@app.post("/search")
async def search(request: SearchRequest):
    """
    Search for relevant documents using retriever
    
    Args:
        request: SearchRequest with query, collection_name, and limit
        
    Returns:
        JSON with search results and context
    """
    state: ServerState = app.state.server_state
    
    if not state.retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    if not state.dense_embedder or not state.sparse_embedder:
        raise HTTPException(status_code=503, detail="Embedding models not initialized")
    
    try:
        logger.info(f"Processing search query: {request.query[:100]}...")
        
        dense_embeddings = state.dense_embedder.encode([request.query])
        dense_embedding = dense_embeddings[0]
        
        sparse_embeddings = state.sparse_embedder.encode([request.query])
        sparse_embedding = sparse_embeddings[0]
        
        context = await state.retriever.search(
            query_text=request.query,
            collection_name=request.collection_name,
            query_dense_embedding=dense_embedding,
            query_sparse_embedding=sparse_embedding,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "collection_name": request.collection_name,
            "context": context,
            "limit": request.limit
        }
    except Exception as e:
        logger.error(f"Failed to perform search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


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