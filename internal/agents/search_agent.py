"""
Search agent tool - Handles document retrieval and question answering
"""
import logging
from pydantic_ai import RunContext

logger = logging.getLogger(__name__)


async def search_documents(
    ctx: RunContext,
    query: str,
    collection_name: str,
    limit: int = 5
) -> str:
    """
    Search documents in a collection and return an answer to the query.
    
    This tool retrieves relevant document chunks, reranks them, optionally
    compresses the context, and generates a natural language answer using LLM.
    
    Args:
        ctx: Pydantic AI run context with ServerState dependencies
        query: User's search query
        collection_name: Name of the collection to search
        limit: Maximum number of results to retrieve (default: 5)
        
    Returns:
        Natural language answer based on retrieved documents
        
    Raises:
        Exception: If search operation fails
    """
    from internal.retriever.retriever import Retriever
    
    state = ctx.deps
    
    logger.info(f"[SEARCH_TOOL] Searching collection '{collection_name}' for: '{query}'")
    
    try:
        # Generate embeddings for the query
        query_dense = state.dense_embedder.encode([query])[0]
        query_sparse = state.sparse_embedder.encode([query])[0]
        
        # Initialize retriever with all necessary components
        retriever = Retriever(
            qdrant_client=state.qdrant_client,
            reranker=state.reranker,
            llm_config=state.llm_config,
            processor=state.processor
        )
        
        response = await retriever.search(
            query_text=query,
            collection_name=collection_name,
            query_dense_embedding=query_dense,
            query_sparse_embedding=query_sparse,
            limit=limit
        )
        
        logger.info(f"[SEARCH_TOOL] Successfully retrieved answer for query")
        return response
        
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        logger.error(f"[SEARCH_TOOL] {error_msg}", exc_info=True)
        return f"I encountered an error while searching: {error_msg}"