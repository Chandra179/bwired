"""
Document Search API Server

FastAPI-based HTTP server for RAG document search with automatic PDF processing.
"""

__version__ = "1.0.0"

# Import app for uvicorn to find it when running as module
from .server import app

__all__ = ['app']