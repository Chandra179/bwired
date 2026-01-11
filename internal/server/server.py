import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_ai import Agent

from internal.embedding.dense_embedder import DenseEmbedder
from internal.embedding.sparse_embedder import SparseEmbedder
from internal.embedding.reranker import Reranker
from internal.storage.qdrant_client import QdrantClient
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
from internal.storage.client import DatabaseClient
from internal.storage.redis_client import RedisClient
from internal.queue.task_queue import TaskQueue
from internal.research.nodes.initiation import generate_seed_questions
from internal.research.nodes.synthesis import (
    collect_facts,
    flatten_to_table,
    build_lineage_graph,
    generate_narrative
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
        
        self.dense_embedder: Optional[DenseEmbedder] = None
        self.sparse_embedder: Optional[SparseEmbedder] = None
        self.reranker: Optional[Reranker] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self.chunker: Optional[BaseDocumentChunker] = None
        self.db_client: Optional[DatabaseClient] = None
        self.redis_client: Optional[RedisClient] = None
        self.task_queue: Optional[TaskQueue] = None
        
        self.agent: Optional[Agent] = None


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
        logger.info("Initializing chunker...")
        state.chunker = ChunkerFactory.create(format='markdown', config=state.config)
        logger.info("✓ Chunker loaded")
    except Exception as e:
        logger.error(f"Failed to load chunker: {e}")
        raise
    
    try:
        logger.info("Initializing database client...")
        if state.config.postgres:
            state.db_client = DatabaseClient(
                database_url=state.config.postgres.url,
                pool_size=state.config.postgres.pool_size,
                max_overflow=state.config.postgres.max_overflow
            )
            await state.db_client.init_db()
            logger.info("✓ Database client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database client: {e}")
        raise
    
    try:
        logger.info("Initializing Redis client...")
        if state.config.redis:
            state.redis_client = RedisClient(
                redis_url=state.config.redis.url,
                db=state.config.redis.db,
                max_connections=state.config.redis.max_connections
            )
            await state.redis_client.connect()
            state.task_queue = TaskQueue(state.redis_client)
            logger.info("✓ Redis client and task queue initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {e}")
        raise
    
    app.state.server_state = state
    
    logger.info("="*60)
    logger.info("✓ Server initialization complete!")
    logger.info("="*60)
    
    yield
    
    logger.info("Shutting down server...")
    if state.db_client:
        await state.db_client.close()
    if state.redis_client:
        await state.redis_client.close()


app = FastAPI(
    title="Document Search API",
    description="RAG-based document search with agentic AI",
    version="2.0.0",
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
        "version": "2.0.0 (Agentic)"
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
            "db_client": "connected" if state.db_client else "failed",
            "redis_client": "connected" if state.redis_client else "failed",
            "task_queue": "loaded" if state.task_queue else "failed",
            "agent": "loaded" if state.agent else "failed"
        }
    }


class StartResearchRequest(BaseModel):
    goal: str
    template_id: str
    depth_limit: Optional[int] = None


@app.post("/research/start")
async def start_research(request: StartResearchRequest):
    """Start a new research task"""
    state: ServerState = app.state.server_state
    
    if not state.db_client:
        raise HTTPException(status_code=500, detail="Database client not initialized")
    
    if not state.config or not state.config.research:
        raise HTTPException(status_code=500, detail="Research configuration not found")
    
    template = await state.db_client.get_template(request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    depth_limit = request.depth_limit or state.config.research.default_depth_limit
    task = await state.db_client.create_research_task(
        goal=request.goal,
        template_id=request.template_id,
        depth_limit=depth_limit
    )
    
    questions = await generate_seed_questions(
        goal=request.goal,
        template={"schema_json": template.schema_json},
        count=state.config.research.seed_question_count
    )
    
    logger.info(f"Created research task {task.id} with {len(questions)} seed questions")
    
    return {
        "task_id": task.id,
        "goal": task.goal,
        "template_id": task.template_id,
        "depth_limit": task.depth_limit,
        "seed_questions": questions,
        "status": task.status
    }


@app.get("/research/{task_id}")
async def get_research_status(task_id: str):
    """Get research task status and progress statistics"""
    from sqlalchemy import select
    
    state: ServerState = app.state.server_state
    
    if not state.db_client:
        raise HTTPException(status_code=500, detail="Database client not initialized")
    
    task = await state.db_client.get_research_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    nodes = await state.db_client.get_nodes_by_task(task_id)
    
    pending_count = sum(1 for n in nodes if n.status == "pending")  # type: ignore
    processing_count = sum(1 for n in nodes if n.status == "processing")  # type: ignore
    completed_count = sum(1 for n in nodes if n.status == "completed")  # type: ignore
    failed_count = sum(1 for n in nodes if n.status == "failed")  # type: ignore
    
    queue_size = 0
    if state.task_queue:
        queue_size = await state.task_queue.get_queue_size()
    
    return {
        "task_id": task.id,
        "goal": task.goal,
        "template_id": task.template_id,
        "depth_limit": task.depth_limit,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,  # type: ignore
        "progress": {
            "total_nodes": len(nodes),
            "pending": pending_count,
            "processing": processing_count,
            "completed": completed_count,
            "failed": failed_count,
            "queue_size": queue_size
        },
        "nodes": [
            {
                "id": n.id,
                "node_type": n.node_type,
                "status": n.status,
                "depth_level": n.depth_level,
                "url": n.url,
                "question_text": n.question_text,
                "priority_score": n.priority_score,
                "created_at": n.created_at.isoformat() if n.created_at else None  # type: ignore
            }
            for n in nodes
        ]
    }


@app.get("/research/{task_id}/result")
async def get_research_result(task_id: str, format: str = "text"):
    """
    Get research results in specified format.
    
    Args:
        task_id: Research task ID
        format: Output format - table, graph, text
    """
    state: ServerState = app.state.server_state
    
    if not state.db_client:
        raise HTTPException(status_code=500, detail="Database client not initialized")
    
    if format not in ["table", "graph", "text"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of: table, graph, text"
        )
    
    task = await state.db_client.get_research_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in ["synthesis_ready", "completed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Task not ready for synthesis. Current status: {task.status}"
        )
    
    facts_list = await collect_facts(task_id, state.db_client)
    
    if not facts_list:
        return {"error": "No facts available for this task"}
    
    if format == "table":
        content = await flatten_to_table(facts_list)
        return {
            "format": "table",
            "content": content,
            "fact_count": len(facts_list)
        }
    
    if format == "graph":
        content = await build_lineage_graph(task_id, state.db_client)
        return {
            "format": "graph",
            "content": content,
            "type": "mermaid"
        }
    
    if format == "text":
        content = await generate_narrative(facts_list, str(task.goal))  # type: ignore
        return {
            "format": "text",
            "content": content,
            "fact_count": len(facts_list)
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