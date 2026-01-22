import logging
import uuid
from typing import Dict, Any, Optional
import numpy as np
from qdrant_client.http.exceptions import UnexpectedResponse

from ..chunkers.base_chunker import BaseDocumentChunker
from ..embedding.dense_embedder import DenseEmbedder
from ..embedding.sparse_embedder import SparseEmbedder
from ..storage.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Handles chunking, embedding, and storage of markdown documents
    
    Workflow:
    1. Auto-generate document ID (UUID)
    2. Chunk document using MarkdownDocumentChunker
    3. Generate dense embeddings
    4. Generate sparse embeddings
    5. Store in Qdrant
    """
    
    def __init__(
        self,
        chunker: BaseDocumentChunker,
        dense_embedder: DenseEmbedder,
        sparse_embedder: SparseEmbedder,
        qdrant_client: QdrantClient
    ):
        self.chunker = chunker
        self.dense_embedder = dense_embedder
        self.sparse_embedder = sparse_embedder
        self.qdrant_client = qdrant_client
        
        logger.info("DocumentProcessor initialized")
    
    async def process_markdown_file(
        self,
        markdown_content: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """
        Process markdown file: chunk → embed → store
        
        Args:
            markdown_content: Raw markdown text
            collection_name: Target Qdrant collection name
            
        Returns:
            Dict with success status and document_id
            
        Raises:
            ValueError: If collection already exists
            Exception: If processing fails
        """
        collection_exists = await self.qdrant_client.client.collection_exists(collection_name)
        if collection_exists:
            raise ValueError(f"Collection '{collection_name}' already exists")
        
        document_id = str(uuid.uuid4())
        logger.info(f"Processing document: {document_id}")
        
        chunks = self.chunker.chunk_document(markdown_content, document_id)
        logger.info(f"Created {len(chunks)} chunks")
        
        chunk_texts = [chunk.content for chunk in chunks]
        dense_embeddings = self.dense_embedder.encode(chunk_texts)
        logger.info(f"Generated {len(dense_embeddings)} dense embeddings")
        
        sparse_embeddings = self.sparse_embedder.encode(chunk_texts)
        logger.info(f"Generated {len(sparse_embeddings)} sparse embeddings")
        
        await self.qdrant_client.initialize(collection_name)
        
        await self.qdrant_client.store_chunks(
            collection_name=collection_name,
            chunks=chunks,
            dense_vectors=dense_embeddings,
            sparse_vectors=sparse_embeddings,
            document_id=document_id
        )
        
        logger.info(f"Successfully processed and stored document: {document_id}")
        
        return {
            "success": True,
            "document_id": document_id,
            "collection_name": collection_name
        }
