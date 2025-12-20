from typing import List, Dict, Any
import logging
import uuid
import hashlib
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, SparseVectorParams, SparseIndexParams,
    Prefetch, Fusion, SparseVector
)
import numpy as np

from ..config import QdrantConfig
from ..core.metadata import ChunkMetadata

logger = logging.getLogger(__name__)


class QdrantStorage:
    
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
            
            vectors_config = {
                "dense": VectorParams(
                    size=self.embedding_dim,
                    distance=distance
                )
            }
            sparse_vectors_config = {
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            }
            await self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config
            )
            logger.info(f"Collection created with dimension {self.embedding_dim}")
        else:
            logger.info(f"Collection {self.config.collection_name} already exists")


    async def store_chunks(
        self, 
        chunks: List[Any],
        embeddings: List[np.ndarray],
        sparse_vectors: List[Dict[str, Any]], 
        document_id: str
    ):
        if len(chunks) != len(embeddings) or len(chunks) != len(sparse_vectors):
            raise ValueError("Mismatch between chunks, dense embeddings, or sparse vectors count")
        
        logger.info(f"Storing {len(chunks)} chunks to Qdrant (Hybrid)")
        
        points = []
        for i, (chunk, embedding, sparse) in enumerate(zip(chunks, embeddings, sparse_vectors)):
            metadata = ChunkMetadata.from_chunk(chunk, document_id)
            
            random_uuid = uuid.uuid4()
            hash_bytes = hashlib.sha256(random_uuid.bytes).digest()
            numeric_id = int.from_bytes(hash_bytes[:8], byteorder='big') % (2**63)
            
            point = PointStruct(
                id=numeric_id,
                vector={
                    "dense": embedding.tolist(),
                    "sparse": SparseVector(
                        indices=sparse["indices"],
                        values=sparse["values"]
                    )
                },
                payload={
                    **metadata.to_dict(),
                    "content": chunk.content
                }
            )
            points.append(point)
            
            if len(points) >= self.config.storage_batch_size:
                await self._upload_batch(points)
                points = []
        
        if points:
            await self._upload_batch(points)
    
    
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
        query_dense_embedding: np.ndarray, 
        query_sparse_indices: List[int],
        query_sparse_values: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using Hybrid Search (Dense + Sparse) with RRF
        
        Args:
            query_dense_embedding: Dense embedding vector
            query_sparse_indices: Indices for the sparse vector
            query_sparse_values: Values for the sparse vector
            limit: Maximum number of results
            
        Returns:
            List of search results with RRF scores and metadata
        """
        try:
            # Note: score_threshold is usually removed for RRF because 
            # RRF scores are calculated based on rank (1/(k+rank)), 
            # not traditional similarity distances.
            
            results = await self.client.query_points(
                collection_name=self.config.collection_name,
                prefetch=[
                    # Prefetch Dense results
                    Prefetch(
                        query=query_dense_embedding.tolist(),
                        using="dense",
                        limit=limit * 2 # Prefetch more to improve fusion quality
                    ),
                    # Prefetch Sparse results
                    Prefetch(
                        query=SparseVector(
                            indices=query_sparse_indices,
                            values=query_sparse_values
                        ),
                        using="sparse",
                        limit=limit * 2
                    ),
                ],
                query=Fusion.RRF,
                limit=limit
            )
            
            return [
                {
                    "rrf_score": result.score,
                    "content": result.payload.get("content"),
                    "metadata": {k: v for k, v in result.payload.items() if k != "content"}
                }
                for result in results.points
            ]
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise