from typing import List, Dict, Any
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
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

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    id: str
    document_id: str
    token_count: int
    chunk_type: str
    parent_section: str
    section_path: str
    next_chunk_id: Optional[str] = None
    prev_chunk_id: Optional[str] = None
    split_sequence: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)        
        return data
    
    @classmethod
    def from_chunk(
        cls,
        chunk,
        document_id: str,
    ) -> 'ChunkMetadata':
        """
        Creates ChunkMetadata from a SemanticChunk.
        Ensures all required positional arguments are passed in order.
        """
        return cls(
            id=chunk.id,
            document_id=document_id,
            token_count=chunk.token_count,
            chunk_type=chunk.chunk_type,
            parent_section=chunk.parent_section, 
            section_path=chunk.section_path,
            next_chunk_id=chunk.next_chunk_id,
            prev_chunk_id=chunk.prev_chunk_id,
            split_sequence=chunk.split_sequence,
        )

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
        
        
    async def initialize(self, collection_name: str):
        """Initialize Qdrant collection if it doesn't exist"""
        logger.info(f"Creating collection: {collection_name}")
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
            collection_name=collection_name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_vectors_config
        )
        logger.info(f"Collection created with dimension {self.dense_embedding_dim}")


    async def store_chunks(
        self, 
        collection_name: str,
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
                await self._upload_batch(collection_name, points)
                points = []
        
        if points:
            await self._upload_batch(collection_name, points)
    
    
    async def _upload_batch(self, collection_name: str, points: List[PointStruct]):
        """Upload a batch of points to Qdrant"""
        try:
            await self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.debug(f"Uploaded batch of {len(points)} points")
        except Exception as e:
            logger.error(f"Failed to upload batch: {e}")
            raise
    
    
    async def query_points(
        self,
        collection_name: str,
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
                collection_name=collection_name,
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