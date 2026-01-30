"""
API module for FastAPI endpoints.

This module contains all API route handlers organized by resource type.
"""

from .health import router as health_router
from .documents import router as documents_router
from .vector_search import router as search_router
from .web_search import router as web_search_router

__all__ = [
    "health_router",
    "documents_router", 
    "search_router",
    "web_search_router",
]
