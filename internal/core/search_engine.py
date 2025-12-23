from typing import List, Dict, Any, Optional
import logging
import numpy as np
from jinja2 import Template
from pathlib import Path

from ..storage.qdrant_client import QdrantClient
from ..embedding.reranker import Reranker
from ..processing.base_processor import BaseProcessor
from ..generator.engine import LocalEngine
from ..config import LLMConfig

logger = logging.getLogger(__name__)


class SearchEngine:
    """High-level search orchestration with reranking, processing, and LLM generation"""
    
    def __init__(
        self, 
        qdrant_client: QdrantClient,
        reranker: Reranker,
        llm_config: LLMConfig,
        processor: Optional[BaseProcessor] = None
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
        self.processor = processor
        self.llm_config = llm_config
        
        # Initialize LLM engine
        self.llm_engine = LocalEngine(model=llm_config.model)
        logger.info(f"LLM Engine initialized with model: {llm_config.model}")
        
        # Load prompt templates
        self.system_template = self._load_template(llm_config.system_prompt_path)
        self.user_template = self._load_template(llm_config.user_prompt_path)
        logger.info("Prompt templates loaded")
        
        logger.info("SearchEngine initialized")
        if processor and processor.is_enabled():
            logger.info(f"Processor enabled: {processor.__class__.__name__}")
        else:
            logger.info("No processor configured")
    
    def _load_template(self, template_path: str) -> Template:
        """
        Load Jinja2 template from file
        
        Args:
            template_path: Path to template file
            
        Returns:
            Jinja2 Template object
        """
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return Template(f.read())
    
    async def search(
        self,
        query_text: str,
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
        
        logger.info("Generating LLM response...")
        response = self._generate_response(query_text, context)
        
        return response
    
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
    
    def _generate_response(self, query: str, context: str) -> str:
        """
        Generate LLM response using query and context
        
        Args:
            query: User query
            context: Retrieved and processed context
            
        Returns:
            Generated response from LLM
        """
        # Render system prompt
        system_prompt = self.system_template.render()
        user_prompt = self.user_template.render(
            query=query,
            context=context
        )
        
        response = self.llm_engine.generate(
            prompt=user_prompt,
            system_message=system_prompt
        )
        
        logger.info("LLM response generated")
        return response