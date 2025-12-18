from typing import List, Dict, Any
import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np

from .config import QdrantConfig
from .metadata import ChunkMetadata

logger = logging.getLogger(__name__)


class QdrantStorage:
    """Handle storage and retrieval from Qdrant vector database (async with gRPC)"""
    
    def __init__(self, config: QdrantConfig, embedding_dim: int):
        self.config = config
        self.embedding_dim = embedding_dim
        host = config.url.replace("http://", "").replace("https://", "").split(":")[0]
        self.client = AsyncQdrantClient(
            host=host,
            grpc_port=config.grpc_port,
            prefer_grpc=True
        )
        logger.info(f"Connecting to Qdrant via gRPC at {host}:{config.grpc_port}")
        logger.info(f"Storage batch size: {config.storage_batch_size}")
        
    async def initialize(self):
        """Initialize the storage (must be called before use)"""
        if self.config.create_if_not_exists:
            await self._ensure_collection_exists()
    
    async def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        collections = await self.client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if self.config.collection_name not in collection_names:
            logger.info(f"Creating collection: {self.config.collection_name}")
            
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclidean": Distance.EUCLID,
                "Dot": Distance.DOT
            }
            
            distance = distance_map.get(self.config.distance_metric, Distance.COSINE)
            
            await self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=distance
                )
            )
            logger.info(f"Collection created with dimension {self.embedding_dim}")
        else:
            logger.info(f"Collection {self.config.collection_name} already exists")
    
    # async def initialize(self):
    #     """Initialize the storage (must be called before use)"""
    #     if self.config.create_if_not_exists:
    #         await self._ensure_collection_exists()
    
    async def store_chunks(
        self, 
        chunks: List[Any],  # List of Chunk objects
        embeddings: List[np.ndarray],
        document_id: str,
        document_title: str
    ):
        """
        Store chunks with embeddings in Qdrant using async batching
        
        Args:
            chunks: List of Chunk objects
            embeddings: List of embedding vectors
            document_id: Document identifier
            document_title: Document title
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) count mismatch")
        
        logger.info(f"Storing {len(chunks)} chunks to Qdrant collection: {self.config.collection_name}")
        logger.info(f"Using batch size: {self.config.storage_batch_size}")
        
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            metadata = ChunkMetadata.from_chunk(chunk, document_id, document_title)
            
            point = PointStruct(
                id=hash(metadata.chunk_id) % (2**63),  # Use hash as numeric ID
                vector=embedding.tolist(),
                payload={
                    **metadata.to_dict(),
                    "content": chunk.content  # Store actual content
                }
            )
            points.append(point)
            
            # Upload in batches
            if len(points) >= self.config.storage_batch_size:
                await self._upload_batch(points)
                points = []
        
        # Upload remaining points
        if points:
            await self._upload_batch(points)
        
        logger.info(f"Successfully stored {len(chunks)} chunks")
    
    async def _upload_batch(self, points: List[PointStruct]):
        """Upload a batch of points asynchronously"""
        try:
            await self.client.upsert(
                collection_name=self.config.collection_name,
                points=points
            )
            logger.debug(f"Uploaded batch of {len(points)} points")
        except Exception as e:
            logger.error(f"Failed to upload batch: {e}")
            raise
    
    async def search(
        self, 
        query_embedding: np.ndarray, 
        limit: int = 10,
        score_threshold: float = 0.6,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            results = await self.client.query_points(
                collection_name=self.config.collection_name,
                query=query_embedding.tolist(),
                limit=limit,
                query_filter=filters,
                score_threshold=score_threshold
            )
            
            return [
                {
                    "score": result.score,
                    "content": result.payload.get("search_content"),
                    "metadata": {k: v for k, v in result.payload.items() if k != "content"}
                }
                for result in results.points
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise