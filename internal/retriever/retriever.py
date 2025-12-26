from typing import List, Dict, Any
import logging
import numpy as np

from ..storage.qdrant_client import QdrantClient
from ..embedding.reranker import Reranker
from ..config import LLMConfig

logger = logging.getLogger(__name__)


class Retriever:
    """High-level search orchestration with reranking, processing, and LLM generation"""
    
    def __init__(
        self, 
        qdrant_client: QdrantClient,
        reranker: Reranker,
        llm_config: LLMConfig,
        processor = None,
    ):
        """
        Initialize search engine
        
        Args:
            qdrant_client: Qdrant client for vector search
            reranker: Reranker for scoring results
            llm_config: Configuration for LLM generation
            processor: Optional processor for post-processing (e.g., compression)
        """
        self.qdrant_client = qdrant_client
        self.reranker = reranker
        self.llm_config = llm_config
        self.processor = processor
        
    
    async def search(
        self,
        query_text: str,
        collection_name: str,
        query_dense_embedding: np.ndarray,
        query_sparse_embedding: Dict[str, Any],
        limit: int = 10
    ) -> str:
        """
        Execute search with reranking, optional processing, and LLM generation
        
        Args:
            query_text: Original query text
            query_dense_embedding: Dense embedding vector for the query
            query_sparse_embedding: Sparse embedding for the query
            limit: Maximum number of results to return
            
        Returns:
            Generated LLM response
        """
        logger.info(f"Retrieving candidates (limit: {limit})...")
        query_response = await self.qdrant_client.query_points(
            collection_name=collection_name,
            query_dense_embedding=query_dense_embedding,
            query_sparse_embedding=query_sparse_embedding,
            limit=limit
        )
        
        points = query_response.points
        if not points:
            logger.warning("No results found")
            return "I couldn't find any relevant information to answer your query."
        
        logger.info(f"Retrieved {len(points)} candidates")
        
        logger.info("Reranking results...")
        reranked_results = self._rerank_results(query_text, points)
        
        # Extract context based on processor availability
        is_processing_enabled = self.processor and self.processor.is_enabled()
        if is_processing_enabled:
            logger.info("Applying processor...")
            processed_output = self.processor.process(reranked_results)
            context = processed_output.get("compressed_context", "")
        else:
            # Extract content from raw results
            context = "\n\n---\n\n".join([
                result["content"] for result in reranked_results
            ])
        
        # Use AI agents refactor this shit
        
        return context
    
    def _rerank_results(self, query_text: str, points: List[Any]) -> List[Dict[str, Any]]:
        """
        Rerank search results using cross-encoder
        
        Args:
            query_text: Original query text
            points: Search results from Qdrant
            
        Returns:
            Reranked results sorted by score
        """
        doc_texts = [p.payload.get("content", "") for p in points]
        query_doc_pairs = [[query_text, doc] for doc in doc_texts]
        
        rerank_scores = self.reranker.predict(query_doc_pairs)
        
        results = []
        for i, score in enumerate(rerank_scores):
            results.append({
                "score": float(score),
                "content": points[i].payload.get("content"),
                "metadata": {k: v for k, v in points[i].payload.items() if k != "content"}
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Reranked {len(results)} results")
        return results