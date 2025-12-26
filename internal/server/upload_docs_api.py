import logging
import tempfile
import re
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from internal.processing.document_extractor import convert_pdf_to_markdown
from internal.chunkers import ChunkerFactory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to create valid collection name
    
    Args:
        filename: Original filename (e.g., "my document.pdf")
        
    Returns:
        Sanitized collection name (e.g., "my_document_pdf")
    """
    if not filename:
        return "unnamed_document"
    
    name = Path(filename).stem
    sanitized = re.sub(r'[^\w\-]', '_', name)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    sanitized = sanitized.lower()
    return sanitized


@router.post("/upload")
async def upload_document(
    req: Request,
    collection_name: str = Form(...),
    file: UploadFile = File(...)
) -> int:
    """
    Upload PDF document, convert to markdown, chunk, embed and store in Qdrant
    
    Args:
        req: FastAPI request object
        collection_name: Optional collection name. If not provided, generated from filename
        file: PDF file to upload
        
    Returns:
        Number of chunks stored
        
    Raises:
        HTTPException: If file processing fails
    """
    state = req.app.state.server_state
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file: no filename")
    
    if not file.content_type or file.content_type != "application/pdf":
        logger.warning(f"File {file.filename} has content type {file.content_type}, expected application/pdf")
    
    collection_name = sanitize_filename(file.filename)
    
    document_id = collection_name
    
    logger.info(f"Processing file: {file.filename} → collection: {collection_name}")
    
    tmp_path = None
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        
        markdown_content = convert_pdf_to_markdown(tmp_path)
        
        logger.info(f"Vectorizing document: {document_id}")
        
        chunks = state.chunker.chunk_document(markdown_content, document_id)
        
        if not chunks:
            raise ValueError("No chunks generated from document. Document may be empty or invalid.")
        
        logger.info(f"Generated {len(chunks)} chunks")
        
        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        dense_embeddings = state.dense_embedder.encode(chunk_texts)
        sparse_embeddings = state.sparse_embedder.encode(chunk_texts)
        
        logger.info(f"Generated embeddings: dense={len(dense_embeddings)}, sparse={len(sparse_embeddings)}")
        
        await state.qdrant_client.initialize(collection_name)
        await state.qdrant_client.store_chunks(
            chunks=chunks,
            dense_vectors=dense_embeddings,
            sparse_vectors=sparse_embeddings,
            document_id=document_id
        )
        
        logger.info(f"Stored {len(chunks)} chunks in collection '{collection_name}'")
        return len(chunks)
        
    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
        
    finally:
        # Clean up temp file
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()