import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from internal.retriever.retriever import Retriever

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    """Request model for search endpoint"""
    query: str
    collection_name: str
    limit: int = 5


class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    response: str


@router.post("/search", response_model=SearchResponse)
async def search_document(
    request: Request,
    search_request: SearchRequest
):
    """
    Search endpoint: Search an existing document collection
    """
    
    state = request.app.state.server_state
    
    logger.info(f"Searching collection '{search_request.collection_name}' with query: '{search_request.query}'")
    
    try:
        query_dense = state.dense_embedder.encode([search_request.query])[0]
        query_sparse = state.sparse_embedder.encode([search_request.query])[0]
        
        search_engine = Retriever(
            qdrant_client=state.qdrant_client,
            reranker=state.reranker,
            llm_config=state.llm_config,
            processor=state.processor
        )
        
        response = await search_engine.search(
            query_text=search_request.query,
            collection_name=request.collection_name,
            query_dense_embedding=query_dense,
            query_sparse_embedding=query_sparse,
            limit=search_request.limit
        )
        
        return SearchResponse(
            response=response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search operation failed: {str(e)}"
        )