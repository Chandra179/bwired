import logging
import tempfile
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from fastapi import APIRouter, UploadFile, File, HTTPException, Request

from internal.processing.document_extractor import convert_pdf_to_markdown

if TYPE_CHECKING:
    from .server import ServerState

logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/extract-pdf")
async def extract_pdf(request: Request, file: UploadFile = File(...)):
    """
    Convert uploaded PDF to markdown using Docling
    
    Args:
        file: PDF file to convert
        
    Returns:
        JSON with converted markdown content
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / file.filename
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        markdown_content = convert_pdf_to_markdown(temp_path)
        
        return {
            "filename": file.filename,
            "markdown": markdown_content,
            "char_count": len(markdown_content)
        }
    except Exception as e:
        logger.error(f"Failed to extract PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract PDF: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/process-markdown-file")
async def process_markdown_file(
    request: Request,
    file: UploadFile = File(...),
    collection_name: str = "documents"
):
    """
    Upload markdown file, chunk, embed, and store in Qdrant
    
    Creates a new collection for each document. Returns error if collection
    already exists.
    
    Args:
        file: Uploaded .md file
        collection_name: Target Qdrant collection name
        
    Returns:
        Simple success/failure response with document_id
    """
    if not file.filename or not file.filename.lower().endswith('.md'):
        raise HTTPException(
            status_code=400,
            detail="File must be a markdown file (.md)"
        )
    
    try:
        markdown_content = await file.read()
        markdown_text = markdown_content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Failed to decode markdown file (must be UTF-8)"
        )
    
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(
            status_code=503,
            detail="Server not properly initialized"
        )
    
    from .server import ServerState
    state: ServerState = request.app.state.server_state
    if not state.document_processor:
        raise HTTPException(
            status_code=503,
            detail="Document processor not initialized"
        )
    
    try:
        result = await state.document_processor.process_markdown_file(
            markdown_content=markdown_text,
            collection_name=collection_name
        )
        return result
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(
                status_code=409,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Failed to process markdown file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process markdown file: {str(e)}"
        )