from typing import List, Dict, Any
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np

from .config import QdrantConfig
from .metadata import ChunkMetadata

logger = logging.getLogger(__name__)


class QdrantStorage:
    """Handle storage and retrieval from Qdrant vector database"""
    
    def __init__(self, config: QdrantConfig, embedding_dim: int):
        self.config = config
        self.embedding_dim = embedding_dim
        
        logger.info(f"Connecting to Qdrant at {config.url}")
        
        # Initialize client
        if config.api_key:
            self.client = QdrantClient(url=config.url, api_key=config.api_key)
        else:
            self.client = QdrantClient(url=config.url)
        
        # Create collection if needed
        if config.create_if_not_exists:
            self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if self.config.collection_name not in collection_names:
            logger.info(f"Creating collection: {self.config.collection_name}")
            
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclidean": Distance.EUCLID,
                "Dot": Distance.DOT
            }
            
            distance = distance_map.get(self.config.distance_metric, Distance.COSINE)
            
            self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=distance
                )
            )
            logger.info(f"Collection created with dimension {self.embedding_dim}")
        else:
            logger.info(f"Collection {self.config.collection_name} already exists")
    
    def store_chunks(
        self, 
        chunks: List[Any],  # List of Chunk objects
        embeddings: List[np.ndarray],
        document_id: str,
        document_title: str,
        batch_size: int = 100
    ):
        """
        Store chunks with embeddings in Qdrant
        
        Args:
            chunks: List of Chunk objects
            embeddings: List of embedding vectors
            document_id: Document identifier
            document_title: Document title
            batch_size: Batch size for uploading
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) count mismatch")
        
        logger.info(f"Storing {len(chunks)} chunks to Qdrant collection: {self.config.collection_name}")
        
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
            if len(points) >= batch_size:
                self._upload_batch(points)
                points = []
        
        # Upload remaining points
        if points:
            self._upload_batch(points)
        
        logger.info(f"Successfully stored {len(chunks)} chunks")
    
    def _upload_batch(self, points: List[PointStruct]):
        """Upload a batch of points"""
        try:
            self.client.upsert(
                collection_name=self.config.collection_name,
                points=points
            )
            logger.debug(f"Uploaded batch of {len(points)} points")
        except Exception as e:
            logger.error(f"Failed to upload batch: {e}")
            raise
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            filters: Optional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            results = self.client.query_points(
                collection_name=self.config.collection_name,
                query=query_embedding.tolist(),  # Argument name changed from 'query_vector' to 'query'
                limit=limit,
                query_filter=filters             # Argument name is likely 'query_filter' or 'filter' depending on exact version
            ).points
            
            return [
                {
                    "score": result.score,
                    "content": result.payload.get("content"),
                    "metadata": {k: v for k, v in result.payload.items() if k != "content"}
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def delete_document(self, document_id: str):
        """Delete all chunks from a document"""
        try:
            self.client.delete(
                collection_name=self.config.collection_name,
                points_selector={
                    "filter": {
                        "must": [
                            {
                                "key": "document_id",
                                "match": {"value": document_id}
                            }
                        ]
                    }
                }
            )
            logger.info(f"Deleted chunks for document: {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            info = self.client.get_collection(self.config.collection_name)
            return {
                "name": info.config.params.name if hasattr(info.config.params, 'name') else self.config.collection_name,
                "vectors_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise