"""
Document search endpoints for the API.

Provides semantic search capabilities using dense and sparse embeddings
with reranking support.
"""

import logging
from typing import TYPE_CHECKING
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from internal.server.server import ServerState


logger = logging.getLogger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    """Request model for document search"""
    query: str
    collection_name: str = "documents"
    limit: int = 10


@router.post("/vector-search")
async def search_documents(request: Request, search_request: SearchRequest):
    """
    Search for relevant documents using retriever
    
    Performs semantic search using dense and sparse embeddings,
    with optional reranking.
    
    Args:
        request: FastAPI Request object
        search_request: SearchRequest with query, collection_name, and limit
        
    Returns:
        JSON with search results and context
    """
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(
            status_code=503,
            detail="Server not properly initialized"
        )
    
    from internal.server.server import ServerState
    state: ServerState = request.app.state.server_state
    
    if not state.retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    if not state.dense_embedder or not state.sparse_embedder:
        raise HTTPException(status_code=503, detail="Embedding models not initialized")
    
    try:
        logger.info(f"Processing search query: {search_request.query[:100]}...")
        
        dense_embeddings = state.dense_embedder.encode([search_request.query])
        dense_embedding = dense_embeddings[0]
        
        sparse_embeddings = state.sparse_embedder.encode([search_request.query])
        sparse_embedding = sparse_embeddings[0]
        
        context = await state.retriever.search(
            query_text=search_request.query,
            collection_name=search_request.collection_name,
            query_dense_embedding=dense_embedding,
            query_sparse_embedding=sparse_embedding,
            limit=search_request.limit
        )
        
        return {
            "query": search_request.query,
            "collection_name": search_request.collection_name,
            "context": context,
            "limit": search_request.limit
        }
    except Exception as e:
        logger.error(f"Failed to perform search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
