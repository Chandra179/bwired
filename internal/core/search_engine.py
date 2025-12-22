from typing import List, Dict, Any, Optional
import logging
import numpy as np

from ..storage.qdrant_client import QdrantClient
from ..embedding.reranker import Reranker
from ..processing.base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class SearchEngine:
    """High-level search orchestration with reranking and optional processing"""
    
    def __init__(
        self, 
        qdrant_client: QdrantClient,
        reranker: Reranker,
        processor: Optional[BaseProcessor] = None
    ):
        """
        Initialize search engine
        
        Args:
            qdrant_client: Qdrant client for vector search
            reranker: Reranker for scoring results
            processor: Optional processor for post-processing (e.g., compression)
        """
        self.qdrant_client = qdrant_client
        self.reranker = reranker
        self.processor = processor
        
        logger.info("SearchEngine initialized")
        if processor and processor.is_enabled():
            logger.info(f"Processor enabled: {processor.__class__.__name__}")
        else:
            logger.info("No processor configured")
    
    async def search(
        self,
        query_text: str,
        query_dense_embedding: np.ndarray,
        query_sparse_embedding: Dict[str, Any],
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Execute search with reranking and optional processing
        
        Args:
            query_text: Original query text
            query_dense_embedding: Dense embedding vector for the query
            query_sparse_embedding: Sparse embedding for the query
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing search results and optional processed output
        """
        logger.info(f"Retrieving candidates (limit: {limit})...")
        query_response = await self.qdrant_client.query_points(
            query_dense_embedding=query_dense_embedding,
            query_sparse_embedding=query_sparse_embedding,
            limit=limit
        )
        
        points = query_response.points
        if not points:
            logger.warning("No results found")
            return {
                "results": [],
                "compressed_context": None
            }
        
        logger.info(f"Retrieved {len(points)} candidates")
        
        logger.info("Reranking results...")
        reranked_results = self._rerank_results(query_text, points)
        
        is_processing_enabled = self.processor and self.processor.is_enabled()
        if is_processing_enabled:
            logger.info("Applying processor...")
            output = self.processor.process(reranked_results)
        else:
            output = {"results": reranked_results}
            
        return self.llm_engine.generate(output)
    
    def _rerank_results(self, query_text: str, points: List[Any]) -> List[Dict[str, Any]]:
        """
        Rerank search results using cross-encoder
        
        Args:
            query_text: Original query text
            points: Search results from Qdrant
            
        Returns:
            Reranked results sorted by score
        """
        # Extract document texts for reranking
        doc_texts = [p.payload.get("content", "") for p in points]
        query_doc_pairs = [[query_text, doc] for doc in doc_texts]
        
        # Get reranker scores
        rerank_scores = self.reranker.predict(query_doc_pairs)
        
        # Build results with reranker scores
        results = []
        for i, score in enumerate(rerank_scores):
            results.append({
                "score": float(score),
                "content": points[i].payload.get("content"),
                "metadata": {k: v for k, v in points[i].payload.items() if k != "content"}
            })
        
        # Sort by reranker score in descending order
        results.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Reranked {len(results)} results")
        return results