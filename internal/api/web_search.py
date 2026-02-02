"""
Web search endpoints for the API.

Provides:
- POST /web-search - General search with bang support
- POST /web-search/specialized - Specialized category search
- GET /web-search/bangs - List available bangs
- GET /web-search/categories - List available categories
"""

import logging
from typing import TYPE_CHECKING, List, Optional, Literal
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Request

from internal.searxng.models import (
    SearXNGSearchRequest,
    SearXNGSearchResponse,
    SpecializedSearchRequest,
    SpecializedSearchResponse,
    BangListResponse,
    CategoryListResponse
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


class WebSearchMarkdownRequest(BaseModel):
    """Request model for web search with markdown conversion"""
    query: str
    category: Optional[str] = None
    language: Optional[str] = "en"
    time_range: Optional[Literal["day", "month", "year"]] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=1000)
    bang: Optional[str] = None
    max_conversions: int = Field(5, ge=1, le=20)
    export_to_file: bool = False


class MarkdownResult(BaseModel):
    """Individual markdown conversion result"""
    url: str
    title: str
    markdown: str
    success: bool
    error: Optional[str] = None
    file_path: Optional[str] = None


class WebSearchMarkdownResponse(BaseModel):
    """Response model for web search with markdown conversion"""
    query: str
    search_results_count: int
    converted_count: int
    failed_count: int
    results: List
    markdown_results: List[MarkdownResult]
    page: int
    per_page: int


@router.post("/web-search", response_model=SearXNGSearchResponse)
async def web_search(request: Request, search_request: SearXNGSearchRequest):
    """
    Search the web using SearXNG with bang syntax support.
    
    Supports:
    - Engine bangs: !gh, !so, !arxiv, !scholar
    - Category bangs: !images, !map, !science, !it, !files, !social
    - Language prefixes: :en, :de, :fr, etc.
    """
    state = _get_state(request)
    
    try:
        logger.info(f"Processing web search: {search_request.query[:100]}...")
        
        return await state.searxng_client.search(
            query=search_request.query,
            category=search_request.category,
            language=search_request.language,
            time_range=search_request.time_range,
            page=search_request.page,
            per_page=search_request.per_page,
            bang=search_request.bang
        )
        
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
        logger.error(f"Web search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Web search failed: {str(e)}")


@router.post("/web-search/specialized", response_model=SpecializedSearchResponse)
async def specialized_search(
    request: Request, 
    search_request: SpecializedSearchRequest
):
    """
    Search using specialized categories.
    
    Supported categories:
    - it: Programming, Linux, IT resources
    - science: Academic papers, scientific databases
    - social: Social media platforms
    - files: Code repositories, file sharing
    - images: Image search
    - map: Maps and locations
    - videos: Video platforms
    - news: News articles
    - general: General web search
    """
    state = _get_state(request)
    
    try:
        logger.info(f"Processing specialized search: {search_request.query[:100]}...")
        
        return await state.searxng_client.search_specialized(search_request)
        
    except BangNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SearXNGTimeoutError:
        raise HTTPException(status_code=504, detail="SearXNG request timeout")
    except SearXNGHTTPError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except SearXNGConnectionError:
        raise HTTPException(status_code=503, detail="SearXNG service unavailable")
    except Exception as e:
        logger.error(f"Specialized search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/web-search/bangs", response_model=BangListResponse)
async def get_bangs(request: Request):
    """Get list of available bang shortcuts"""
    state = _get_state(request)
    
    try:
        available_bangs = await state.searxng_client.get_available_bangs()
        return BangListResponse(bangs=available_bangs)
        
    except Exception as e:
        logger.error(f"Failed to get bangs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bangs: {str(e)}")


@router.get("/web-search/categories", response_model=CategoryListResponse)
async def get_categories(request: Request):
    """Get list of available search categories"""
    state = _get_state(request)
    
    try:
        categories = await state.searxng_client.get_categories()
        return CategoryListResponse(categories=categories)
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.get("/web-search/bangs/syntax")
async def get_bang_syntax_help(request: Request):
    """Get help documentation for bang syntax usage"""
    state = _get_state(request)
    
    bangs = await state.searxng_client.get_available_bangs()
    
    # Organize by category
    engine_bangs = {}
    category_bangs = {}
    
    for bang, config in bangs.items():
        if config.engine:
            if config.engine not in engine_bangs:
                engine_bangs[config.engine] = []
            engine_bangs[config.engine].append({
                "bang": bang,
                "name": config.name,
                "description": config.description
            })
        elif config.category:
            if config.category not in category_bangs:
                category_bangs[config.category] = []
            category_bangs[config.category].append({
                "bang": bang,
                "name": config.name,
                "description": config.description
            })
    
    return {
        "language_prefixes": BangRegistry.LANGUAGE_PREFIXES,
        "engine_bangs": engine_bangs,
        "category_bangs": category_bangs,
        "examples": {
            "github_search": "!gh python web framework",
            "stackoverflow_search": "!so how to use fastapi",
            "arxiv_search": "!arxiv transformer attention mechanism",
            "images_search": "!images cute cats",
            "maps_search": "!map coffee shops nearby",
            "language_prefix": ":de machine learning tutorial",
            "combined": ":de !gh rust async"
        }
    }


def _get_state(request: Request) -> "ServerState":
    """Get server state from request"""
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(status_code=503, detail="Server not properly initialized")
    
    state = request.app.state.server_state
    
    if not state.searxng_client:
        raise HTTPException(status_code=503, detail="SearXNG client not initialized")
    
    return state


# Import BangRegistry at bottom to avoid circular imports
from internal.searxng.bangs import BangRegistry
