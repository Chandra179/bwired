from typing import List, Dict, Any
import logging
import uuid
import hashlib
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, SparseVectorParams, SparseIndexParams,
    Prefetch, Fusion, SparseVector, FusionQuery
)
from qdrant_client.http.models import QueryResponse
import numpy as np

from ..config import QdrantConfig
from ..retriever.metadata import ChunkMetadata

logger = logging.getLogger(__name__)


class QdrantClient:
    """Low-level Qdrant operations for vector storage and retrieval"""
    
    def __init__(self, config: QdrantConfig, dense_embedding_dim: int):
        """
        Initialize Qdrant client
        
        Args:
            config: Qdrant configuration
            dense_embedding_dim: Dimension of dense embeddings
        """
        self.config = config
        self.dense_embedding_dim = dense_embedding_dim
        host = config.url.replace("http://", "").replace("https://", "").split(":")[0]
        self.client = AsyncQdrantClient(
            host=host,
            grpc_port=config.grpc_port,
            prefer_grpc=True
        )
        logger.info(f"Connecting to Qdrant via gRPC at {host}:{config.grpc_port}")
        logger.info(f"Storage batch size: {config.storage_batch_size}")
        
        
    async def initialize(self):
        """Initialize Qdrant collection if it doesn't exist"""
        collections = await self.client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if self.config.collection_name not in collection_names:
            logger.info(f"Creating collection: {self.config.collection_name}")
            
            vectors_config = {
                "dense": VectorParams(
                    size=self.dense_embedding_dim,
                    distance=Distance.COSINE
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
            logger.info(f"Collection created with dimension {self.dense_embedding_dim}")
        else:
            logger.info(f"Collection {self.config.collection_name} already exists")


    async def store_chunks(
        self, 
        chunks: List[Any],
        dense_vectors: List[np.ndarray],
        sparse_vectors: List[Dict[str, Any]], 
        document_id: str
    ):
        """
        Store chunks with their embeddings in Qdrant
        
        Args:
            chunks: List of document chunks
            dense_vectors: List of dense embedding vectors
            sparse_vectors: List of sparse embedding vectors
            document_id: ID of the source document
        """
        if len(chunks) != len(dense_vectors) or len(chunks) != len(sparse_vectors):
            raise ValueError("Mismatch between chunks, dense embeddings, or sparse vectors count")
        
        logger.info(f"Storing {len(chunks)} chunks to Qdrant")
        
        points = []
        for i, (chunk, dense, sparse) in enumerate(zip(chunks, dense_vectors, sparse_vectors)):
            metadata = ChunkMetadata.from_chunk(chunk, document_id)
            
            random_uuid = uuid.uuid4()
            hash_bytes = hashlib.sha256(random_uuid.bytes).digest()
            numeric_id = int.from_bytes(hash_bytes[:8], byteorder='big') % (2**63)
            
            point = PointStruct(
                id=numeric_id,
                vector={
                    "dense": dense.tolist(),
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
        """Upload a batch of points to Qdrant"""
        try:
            await self.client.upsert(
                collection_name=self.config.collection_name,
                points=points
            )
            logger.debug(f"Uploaded batch of {len(points)} points")
        except Exception as e:
            logger.error(f"Failed to upload batch: {e}")
            raise
    
    
    async def query_points(
        self, 
        query_dense_embedding: np.ndarray, 
        query_sparse_embedding: Dict[str, Any],
        limit: int = 10,
    ) -> QueryResponse:
        """
        Perform hybrid search using dense and sparse vectors with RRF fusion
        
        Args:
            query_dense_embedding: Dense embedding vector for the query
            query_sparse_embedding: Sparse embedding for the query
            limit: Maximum number of results to return
            
        Returns:
            QueryResponse from Qdrant containing search results
        """
        try:
            sparse_indices = query_sparse_embedding.get("indices", [])
            sparse_values = query_sparse_embedding.get("values", [])
            candidate_pool_limit = 10
            
            # Perform hybrid search with RRF
            results = await self.client.query_points(
                collection_name=self.config.collection_name,
                prefetch=[
                    Prefetch(
                        query=query_dense_embedding.tolist(),
                        using="dense",
                        limit=candidate_pool_limit
                    ),
                    Prefetch(
                        query=SparseVector(
                            indices=sparse_indices,
                            values=sparse_values
                        ),
                        using="sparse",
                        limit=candidate_pool_limit
                    ),
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=limit
            )
            
            return results
    
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise