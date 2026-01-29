"""
Health check endpoints for the API.

Provides basic and detailed health status endpoints for monitoring
and service discovery.
"""

from typing import TYPE_CHECKING
from fastapi import APIRouter, Request

if TYPE_CHECKING:
    from internal.server.server import ServerState


router = APIRouter()


@router.get("/")
async def root(request: Request):
    """Root health check endpoint"""
    return {
        "status": "online",
        "message": "Document Search API is running",
        "version": "2.1.0"
    }


@router.get("/health")
async def health(request: Request):
    """Detailed health check with component status"""
    if hasattr(request.app.state, 'server_state'):
        from internal.server.server import ServerState
        state: ServerState = request.app.state.server_state
        return {
            "status": "healthy",
            "models": {
                "dense_embedder": "loaded" if state.dense_embedder else "failed",
                "sparse_embedder": "loaded" if state.sparse_embedder else "failed",
                "reranker": "loaded" if state.reranker else "failed",
                "qdrant_client": "connected" if state.qdrant_client else "failed",
                "retriever": "loaded" if state.retriever else "failed",
                "document_processor": "loaded" if state.document_processor else "failed",
                "searxng_client": "loaded" if state.searxng_client else "failed"
            }
        }
    else:
        return {
            "status": "starting",
            "message": "Server is still initializing"
        }
