"""
Research retriever for hybrid search over session-specific collections.

Provides retrieval functionality filtered by session_id with hybrid
dense + sparse search and optional reranking.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np
from qdrant_client.models import Filter, FieldCondition, MatchValue

from internal.config import ExtractionConfig, RerankerConfig
from internal.storage.qdrant_client import QdrantClient
from internal.embedding.dense_embedder import DenseEmbedder
from internal.embedding.sparse_embedder import SparseEmbedder

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A chunk retrieved from vector search."""
    chunk_id: str
    content: str
    score: float
    source_url: str
    domain: str
    seed_question: Optional[str]
    section_path: Optional[str]
    document_id: str
    
    @classmethod
    def from_qdrant_point(cls, point: Any) -> 'RetrievedChunk':
        """Create from Qdrant query result point."""
        payload = point.payload or {}
        return cls(
            chunk_id=payload.get('id', str(point.id)),
            content=payload.get('content', ''),
            score=point.score if hasattr(point, 'score') else 0.0,
            source_url=payload.get('source_url', ''),
            domain=payload.get('domain', ''),
            seed_question=payload.get('seed_question'),
            section_path=payload.get('section_path'),
            document_id=payload.get('document_id', '')
        )


@dataclass 
class RetrievalResult:
    """Result from a retrieval operation."""
    query: str
    chunks: List[RetrievedChunk]
    total_found: int
    session_id: str


class ResearchRetriever:
    """
    Retriever for research session content.
    
    Performs hybrid search (dense + sparse) over session-specific
    Qdrant collections with optional filtering and reranking.
    """
    
    def __init__(
        self,
        qdrant_client: QdrantClient,
        dense_embedder: DenseEmbedder,
        sparse_embedder: SparseEmbedder,
        config: ExtractionConfig,
        reranker: Optional[Any] = None,
        reranker_config: Optional[RerankerConfig] = None
    ):
        """
        Initialize the research retriever.
        
        Args:
            qdrant_client: Qdrant client for vector operations
            dense_embedder: Dense embedding model
            sparse_embedder: Sparse embedding model (SPLADE)
            config: Extraction config with retrieval_top_k setting
            reranker: Optional reranker model for result refinement
            reranker_config: Optional reranker configuration
        """
        self.qdrant_client = qdrant_client
        self.dense_embedder = dense_embedder
        self.sparse_embedder = sparse_embedder
        self.config = config
        self.reranker = reranker
        self.reranker_config = reranker_config
        
        logger.info(f"Initialized ResearchRetriever with top_k={config.retrieval_top_k}")
    
    async def retrieve_for_question(
        self,
        question: str,
        session_id: str,
        top_k: Optional[int] = None,
        filter_by_seed_question: Optional[str] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks for a question from a research session.
        
        Uses hybrid search (dense + sparse) with RRF fusion over the
        session-specific collection.
        
        Args:
            question: The question/query to search for
            session_id: Research session ID to search within
            top_k: Number of results to return (defaults to config.retrieval_top_k)
            filter_by_seed_question: Optional filter to only include chunks
                                     from a specific seed question
            
        Returns:
            RetrievalResult with ranked chunks
        """
        top_k = top_k or self.config.retrieval_top_k
        collection_name = f"research_{session_id}"
        
        logger.debug(f"Retrieving for question: '{question[:50]}...' from {collection_name}")
        
        # Generate embeddings for the query
        dense_embedding = self.dense_embedder.encode([question])[0]
        sparse_embedding = self.sparse_embedder.encode([question])[0]
        
        try:
            # Perform hybrid search
            results = await self.qdrant_client.query_points(
                collection_name=collection_name,
                query_dense_embedding=dense_embedding,
                query_sparse_embedding=sparse_embedding,
                limit=top_k * 2 if self.reranker else top_k  # Get more for reranking
            )
            
            # Convert to RetrievedChunk objects
            chunks = []
            for point in results.points:
                chunk = RetrievedChunk.from_qdrant_point(point)
                
                # Apply seed question filter if specified
                if filter_by_seed_question:
                    if chunk.seed_question != filter_by_seed_question:
                        continue
                
                chunks.append(chunk)
            
            # Apply reranking if available
            if self.reranker and self.reranker_config and self.reranker_config.enabled:
                chunks = self._rerank_chunks(question, chunks, top_k)
            else:
                # Just take top_k
                chunks = chunks[:top_k]
            
            logger.debug(f"Retrieved {len(chunks)} chunks for question")
            
            return RetrievalResult(
                query=question,
                chunks=chunks,
                total_found=len(results.points),
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return RetrievalResult(
                query=question,
                chunks=[],
                total_found=0,
                session_id=session_id
            )
    
    async def retrieve_for_questions(
        self,
        questions: List[str],
        session_id: str,
        top_k: Optional[int] = None
    ) -> Dict[str, RetrievalResult]:
        """
        Retrieve relevant chunks for multiple questions.
        
        Args:
            questions: List of questions to search for
            session_id: Research session ID
            top_k: Results per question
            
        Returns:
            Dict mapping question -> RetrievalResult
        """
        import asyncio
        
        tasks = [
            self.retrieve_for_question(q, session_id, top_k)
            for q in questions
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        result_dict = {}
        for question, result in zip(questions, results):
            if isinstance(result, Exception):
                logger.error(f"Retrieval failed for '{question}': {result}")
                result_dict[question] = RetrievalResult(
                    query=question,
                    chunks=[],
                    total_found=0,
                    session_id=session_id
                )
            else:
                result_dict[question] = result
        
        return result_dict
    
    async def retrieve_all_chunks(
        self,
        session_id: str,
        limit: int = 1000
    ) -> List[RetrievedChunk]:
        """
        Retrieve all chunks from a session collection.
        
        Useful for batch processing all content in a session.
        
        Args:
            session_id: Research session ID
            limit: Maximum chunks to retrieve
            
        Returns:
            List of all chunks in the collection
        """
        collection_name = f"research_{session_id}"
        
        try:
            # Scroll through all points in collection
            chunks = []
            offset = None
            
            while len(chunks) < limit:
                batch_size = min(100, limit - len(chunks))
                
                # Use scroll to get all points
                records, next_offset = await self.qdrant_client.client.scroll(
                    collection_name=collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                for record in records:
                    payload = record.payload or {}
                    chunk = RetrievedChunk(
                        chunk_id=payload.get('id', str(record.id)),
                        content=payload.get('content', ''),
                        score=0.0,  # No score for scroll
                        source_url=payload.get('source_url', ''),
                        domain=payload.get('domain', ''),
                        seed_question=payload.get('seed_question'),
                        section_path=payload.get('section_path'),
                        document_id=payload.get('document_id', '')
                    )
                    chunks.append(chunk)
                
                if next_offset is None or len(records) < batch_size:
                    break
                    
                offset = next_offset
            
            logger.info(f"Retrieved {len(chunks)} total chunks from session {session_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to retrieve all chunks: {e}")
            return []
    
    def _rerank_chunks(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_k: int
    ) -> List[RetrievedChunk]:
        """
        Rerank chunks using the reranker model.
        
        Args:
            query: The search query
            chunks: Chunks to rerank
            top_k: Number of top results to return
            
        Returns:
            Reranked and filtered chunks
        """
        if not chunks:
            return []
        
        try:
            # Prepare pairs for reranking
            pairs = [(query, chunk.content) for chunk in chunks]
            
            # Get reranker scores - reranker can be CrossEncoder or similar
            if hasattr(self.reranker, 'compute_score'):
                scores = self.reranker.compute_score(pairs)
            elif hasattr(self.reranker, 'predict'):
                scores = self.reranker.predict(pairs)
            else:
                logger.warning("Reranker has no known scoring method")
                return chunks[:top_k]
            
            # Handle both single score and list of scores
            if isinstance(scores, (int, float)):
                scores = [scores]
            
            # Sort by reranker score
            scored_chunks = list(zip(chunks, scores))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            
            # Update scores and return top_k
            result = []
            for chunk, score in scored_chunks[:top_k]:
                chunk.score = float(score)
                result.append(chunk)
            
            return result
            
        except Exception as e:
            logger.warning(f"Reranking failed, returning original order: {e}")
            return chunks[:top_k]
    
    async def get_collection_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics about a research session's collection.
        
        Args:
            session_id: Research session ID
            
        Returns:
            Dict with collection statistics
        """
        collection_name = f"research_{session_id}"
        
        try:
            info = await self.qdrant_client.client.get_collection(collection_name)
            
            return {
                "collection_name": collection_name,
                "points_count": info.points_count,
                "indexed_vectors_count": getattr(info, 'indexed_vectors_count', None),
                "status": info.status.value if info.status else "unknown"
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "collection_name": collection_name,
                "error": str(e)
            }
