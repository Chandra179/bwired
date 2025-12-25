import logging
import tempfile
import re
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from pydantic import BaseModel

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat

from internal.chunkers import ChunkerFactory
from internal.storage.qdrant_client import QdrantClient
from internal.core.search_engine import SearchEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    response: str
    collection_name: str


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to create valid collection name
    
    Args:
        filename: Original filename (e.g., "my document.pdf")
        
    Returns:
        Sanitized collection name (e.g., "my_document_pdf")
    """
    # Remove extension
    name = Path(filename).stem
    
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[^\w\-]', '_', name)
    
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Convert to lowercase for consistency
    sanitized = sanitized.lower()
    
    return sanitized


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    """
    Convert PDF to markdown using Docling
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Markdown content as string
    """
    logger.info(f"Converting PDF to markdown: {pdf_path.name}")
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.generate_picture_images = False
    pipeline_options.generate_page_images = False
    
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    result = converter.convert(pdf_path)
    markdown_content = result.document.export_to_markdown()
    
    logger.info(f"PDF converted successfully ({len(markdown_content)} chars)")
    return markdown_content


async def check_collection_exists(qdrant_config, collection_name: str, dense_dim: int) -> bool:
    """
    Check if a collection exists in Qdrant
    
    Args:
        qdrant_config: Qdrant configuration
        collection_name: Name of collection to check
        dense_dim: Dimension for dense embeddings
        
    Returns:
        True if collection exists, False otherwise
    """
    # Create temporary client to check collection
    host = qdrant_config.url.replace("http://", "").replace("https://", "").split(":")[0]
    
    from qdrant_client import AsyncQdrantClient
    client = AsyncQdrantClient(
        host=host,
        grpc_port=qdrant_config.grpc_port,
        prefer_grpc=True
    )
    
    try:
        collections = await client.get_collections()
        collection_names = [col.name for col in collections.collections]
        return collection_name in collection_names
    finally:
        await client.close()


async def vectorize_document(
    markdown_content: str,
    collection_name: str,
    document_id: str,
    state
):
    """
    Vectorize markdown document and store in Qdrant
    
    Args:
        markdown_content: Markdown text content
        collection_name: Collection name to store in
        document_id: Document identifier
        state: Server state with models and configs
    """
    logger.info(f"Vectorizing document: {document_id}")
    
    chunker = ChunkerFactory.create(format='markdown', config=state.rag_config)
    chunks = chunker.chunk_document(markdown_content, document_id)
    
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No chunks generated from document. Document may be empty or invalid."
        )
    
    logger.info(f"Generated {len(chunks)} chunks")
    
    # Generate embeddings
    chunk_texts = [chunk.content for chunk in chunks]
    dense_embeddings = state.dense_embedder.encode(chunk_texts)
    sparse_embeddings = state.sparse_embedder.encode(chunk_texts)
    
    logger.info(f"Generated embeddings: dense={len(dense_embeddings)}, sparse={len(sparse_embeddings)}")
    
    # Create Qdrant client with specific collection name
    from internal.config import QdrantConfig
    qdrant_config = QdrantConfig(
        url=state.qdrant_config.url,
        collection_name=collection_name,
        distance_metric=state.qdrant_config.distance_metric,
        grpc_port=state.qdrant_config.grpc_port,
        storage_batch_size=state.qdrant_config.storage_batch_size
    )
    
    storage = QdrantClient(qdrant_config, state.dense_embedder.get_dimension())
    
    await storage.initialize()
    await storage.store_chunks(
        chunks=chunks,
        dense_vectors=dense_embeddings,
        sparse_vectors=sparse_embeddings,
        document_id=document_id
    )
    
    logger.info(f"Stored {len(chunks)} chunks in collection '{collection_name}'")
    
    return len(chunks)


async def perform_search(
    query: str,
    collection_name: str,
    state,
    limit: int = 5
) -> str:
    """
    Perform search on specified collection
    
    Args:
        query: Search query
        collection_name: Collection to search in
        state: Server state with models and configs
        limit: Number of results to retrieve
        
    Returns:
        LLM generated response
    """
    logger.info(f"Searching collection '{collection_name}' with query: '{query}'")
    
    # Generate query embeddings
    query_dense = state.dense_embedder.encode([query])[0]
    query_sparse = state.sparse_embedder.encode([query])[0]
    
    # Create Qdrant client for this collection
    from internal.config import QdrantConfig
    qdrant_config = QdrantConfig(
        url=state.qdrant_config.url,
        collection_name=collection_name,
        distance_metric=state.qdrant_config.distance_metric,
        grpc_port=state.qdrant_config.grpc_port,
        storage_batch_size=state.qdrant_config.storage_batch_size
    )
    
    qdrant_client = QdrantClient(qdrant_config, state.dense_embedder.get_dimension())
    
    # Create search engine
    search_engine = SearchEngine(
        qdrant_client=qdrant_client,
        reranker=state.reranker,
        llm_config=state.llm_config,
        processor=state.processor
    )
    
    # Perform search
    response = await search_engine.search(
        query_text=query,
        query_dense_embedding=query_dense,
        query_sparse_embedding=query_sparse,
        limit=limit
    )
    
    return response


@router.post("/search", response_model=SearchResponse)
async def search_document(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF file to search")],
    query: Annotated[str, Form(description="Search query")]
):
    """
    Search endpoint: Upload PDF and query to get LLM response
    """
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Get server state
    state = request.app.state.server_state
    
    collection_name = sanitize_filename(file.filename)
    document_id = collection_name
    
    logger.info(f"Processing file: {file.filename} → collection: {collection_name}")
    
    try:
        collection_exists = await check_collection_exists(
            state.qdrant_config,
            collection_name,
            state.dense_embedder.get_dimension()
        )
        
        num_chunks = 0
        
        if collection_exists:
            logger.info(f"Collection '{collection_name}' already exists, skipping vectorization")
        else:
            logger.info(f"Collection '{collection_name}' not found, starting vectorization...")
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)
            
            try:
                markdown_content = convert_pdf_to_markdown(tmp_path)
                num_chunks = await vectorize_document(
                    markdown_content,
                    collection_name,
                    document_id,
                    state
                )
                
            finally:
                # Clean up temporary file
                tmp_path.unlink()
        
        llm_response = await perform_search(
            query=query,
            collection_name=collection_name,
            state=state,
            limit=5
        )
        
        return SearchResponse(
            response=llm_response,
            collection_name=collection_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search operation failed: {str(e)}"
        )