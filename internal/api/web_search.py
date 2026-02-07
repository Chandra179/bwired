"""
Simplified search API endpoints.

Provides:
- POST /search - Unified search across books, science, and social media
- GET /search/categories - List available categories with engines and examples
"""

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request

from internal.searxng.models import (
    SearchRequest,
    SearchResponse,
    CategoryListResponse,
    EnginesListResponse
)
from internal.searxng.exceptions import (
    SearXNGTimeoutError,
    SearXNGConnectionError,
    SearXNGHTTPError,
    SearXNGInvalidResponseError,
    BangNotFoundError
)

if TYPE_CHECKING:
    from internal.server.server import ServerState

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, search_request: SearchRequest):
    """
    Search across books, science, and social media.
    
    **Categories:**
    - `books`: OpenLibrary, Anna's Archive
    - `science`: arXiv, Google Scholar
    - `social_media`: Reddit
    
    **Bang Shortcuts:**
    - `!ol` - OpenLibrary (books)
    - `!aa` - Anna's Archive (books)
    - `!arxiv` - arXiv (science)
    - `!gos` - Google Scholar (science)
    - `!re` - Reddit (social_media)
    - `!books` - All book sources
    - `!science` - All science sources
    - `!social` - All social media sources
    
    **Examples:**
    - Search books: `query="!ol python programming"` or `category="books"`
    - Search science: `query="!arxiv quantum computing"` or `category="science"`
    - Search Reddit: `query="!re web development"` or `category="social_media"`
    """
    state = _get_state(request)
    
    try:
        logger.info(f"Processing search: {search_request.query[:100]}...")
        
        return await state.searxng_client.search(search_request)
        
    except BangNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SearXNGTimeoutError:
        raise HTTPException(status_code=504, detail="SearXNG request timeout")
    except SearXNGHTTPError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except SearXNGConnectionError:
        raise HTTPException(status_code=503, detail="SearXNG service unavailable")
    except SearXNGInvalidResponseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/categories", response_model=CategoryListResponse)
async def get_categories(request: Request):
    """
    Get available search categories with engines and usage examples.
    
    Returns 4 categories:
    - **books**: OpenLibrary (!ol), Anna's Archive (!aa)
    - **science**: arXiv (!arxiv), Google Scholar (!gos)
    - **social_media**: Reddit (!re)
    - **news**: DuckDuckGo News (!ddn), Presearch News (!psn)
    
    Each category includes:
    - List of engines
    - Available bang shortcuts
    - Usage examples
    """
    state = _get_state(request)
    
    try:
        categories = await state.searxng_client.get_categories()
        return CategoryListResponse(categories=categories)
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.get("/search/engines", response_model=EnginesListResponse)
async def get_engines(request: Request):
    """
    Get available search engines grouped by category.
    
    Returns all engines organized by their category:
    - **books**: openlibrary, annas archive
    - **science**: arxiv, google scholar
    - **social_media**: reddit
    - **news**: duckduckgo news, presearch news
    
    Each engine includes its name, bang shortcut, and description.
    """
    state = _get_state(request)
    
    try:
        engines = await state.searxng_client.get_engines()
        return EnginesListResponse(engines=engines)
        
    except Exception as e:
        logger.error(f"Failed to get engines: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get engines: {str(e)}")


def _get_state(request: Request) -> "ServerState":
    """Get server state from request"""
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(status_code=503, detail="Server not properly initialized")
    
    state = request.app.state.server_state
    
    if not state.searxng_client:
        raise HTTPException(status_code=503, detail="SearXNG client not initialized")
    
    return state
