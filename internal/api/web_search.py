"""
Web search endpoints for the API.

Provides SearXNG web search integration with optional markdown conversion
for fetched URLs.
"""

import logging
from typing import TYPE_CHECKING, List, Optional, Literal
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Request

from internal.searxng.models import (
    SearXNGSearchRequest,
    SearXNGSearchResponse,
    SearXNGResult,
    BangSyntaxRequest,
    BangListResponse
)
from internal.searxng.exceptions import (
    SearXNGTimeoutError,
    SearXNGConnectionError,
    SearXNGHTTPError,
    SearXNGInvalidResponseError
)
from internal.processing.document_extractor import convert_urls_to_markdown

if TYPE_CHECKING:
    from internal.server.server import ServerState

logger = logging.getLogger(__name__)
router = APIRouter()


class WebSearchMarkdownRequest(BaseModel):
    """Request model for web search with markdown conversion"""
    query: str
    categories: Optional[str] = Field("general", description="general, news, science, images, videos, files, it, map")
    language: Optional[str] = Field("en", description="Language code")
    time_range: Optional[Literal["day", "week", "month", "year"]] = None
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination")
    per_page: Optional[int] = Field(10, ge=1, le=1000, description="Results per page (max 1000)")
    bang: Optional[str] = Field(None, description="Bang shortcut (e.g., '!news', '!go', '!yhn')")
    max_conversions: Optional[int] = Field(5, ge=1, le=20, description="Maximum number of results to convert to markdown")


class MarkdownResult(BaseModel):
    """Individual markdown conversion result"""
    url: str
    title: str
    markdown: str
    success: bool
    error: Optional[str] = None


class WebSearchMarkdownResponse(BaseModel):
    """Response model for web search with markdown conversion"""
    query: str
    search_results_count: int
    converted_count: int
    failed_count: int
    search_results: List[SearXNGResult]
    markdown_results: List[MarkdownResult]
    page: int
    per_page: int


@router.post("/web-search", response_model=SearXNGSearchResponse)
async def web_search(request: Request, search_request: SearXNGSearchRequest):
    """
    Search the web using SearXNG API
    
    Performs a web search with optional category filtering, time ranges,
    and bang syntax shortcuts.
    """
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(
            status_code=503,
            detail="Server not properly initialized"
        )
    
    from internal.server.server import ServerState
    state: ServerState = request.app.state.server_state
    
    if not state.searxng_client:
        raise HTTPException(status_code=503, detail="SearXNG client not initialized")
    
    try:
        logger.info(f"Processing web search query: {search_request.query[:100]}...")
        
        return await state.searxng_client.search(
            query=search_request.query,
            categories=search_request.categories,
            language=search_request.language,
            time_range=search_request.time_range,
            page=search_request.page,
            per_page=search_request.per_page,
            bang=search_request.bang
        )
        
    except SearXNGTimeoutError:
        logger.error("SearXNG request timeout")
        raise HTTPException(status_code=504, detail="SearXNG request timeout")
    except SearXNGHTTPError as e:
        logger.error(f"SearXNG HTTP error: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except SearXNGConnectionError:
        logger.error("Failed to connect to SearXNG")
        raise HTTPException(status_code=503, detail="SearXNG service unavailable")
    except SearXNGInvalidResponseError as e:
        logger.error(f"SearXNG invalid response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to perform web search: {e}")
        raise HTTPException(status_code=500, detail=f"Web search failed: {str(e)}")


@router.post("/web-search/bang", response_model=SearXNGSearchResponse)
async def web_search_with_bang(request: Request, bang_request: BangSyntaxRequest):
    """
    Search using bang syntax shortcuts
    
    Bang shortcuts allow searching specific engines directly.
    Examples: !go (Google), !yhn (Yahoo News), !re (Reddit)
    """
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(
            status_code=503,
            detail="Server not properly initialized"
        )
    
    from internal.server.server import ServerState
    state: ServerState = request.app.state.server_state
    
    if not state.searxng_client:
        raise HTTPException(status_code=503, detail="SearXNG client not initialized")
    
    try:
        logger.info(f"Processing bang search: {bang_request.bang} {bang_request.query[:100]}...")
        
        return await state.searxng_client.search_with_bang(
            query=bang_request.query,
            bang=bang_request.bang,
            categories=bang_request.categories,
            language=bang_request.language,
            time_range=bang_request.time_range,
            page=bang_request.page,
            per_page=bang_request.per_page
        )
        
    except SearXNGTimeoutError:
        logger.error("SearXNG request timeout")
        raise HTTPException(status_code=504, detail="SearXNG request timeout")
    except SearXNGHTTPError as e:
        logger.error(f"SearXNG HTTP error: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except SearXNGConnectionError:
        logger.error("Failed to connect to SearXNG")
        raise HTTPException(status_code=503, detail="SearXNG service unavailable")
    except SearXNGInvalidResponseError as e:
        logger.error(f"SearXNG invalid response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to perform bang search: {e}")
        raise HTTPException(status_code=500, detail=f"Bang search failed: {str(e)}")


@router.get("/web-search/bangs", response_model=BangListResponse)
async def get_available_bangs(request: Request):
    """
    Get list of available bang shortcuts and their descriptions
    
    Returns all supported bang shortcuts that can be used with
    the /web-search/bang endpoint.
    """
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(
            status_code=503,
            detail="Server not properly initialized"
        )
    
    from internal.server.server import ServerState
    state: ServerState = request.app.state.server_state
    
    if not state.searxng_client:
        raise HTTPException(status_code=503, detail="SearXNG client not initialized")
    
    try:
        logger.info("Getting available bang shortcuts")
        available_bangs = await state.searxng_client.get_available_bangs()
        return BangListResponse(available_bangs=available_bangs)
        
    except Exception as e:
        logger.error(f"Failed to get available bangs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bangs: {str(e)}")


@router.post("/web-search/markdown", response_model=WebSearchMarkdownResponse)
async def web_search_markdown(request: Request, search_request: WebSearchMarkdownRequest):
    """
    Search the web using SearXNG and convert result URLs to markdown
    
    Performs a web search, then fetches and converts the top results
    to markdown format using Docling.
    
    Args:
        request: FastAPI Request object
        search_request: WebSearchMarkdownRequest with search parameters
        
    Returns:
        WebSearchMarkdownResponse with search results and converted markdown
    """
    if not hasattr(request.app.state, 'server_state'):
        raise HTTPException(
            status_code=503,
            detail="Server not properly initialized"
        )
    
    from internal.server.server import ServerState
    state: ServerState = request.app.state.server_state
    
    if not state.searxng_client:
        raise HTTPException(status_code=503, detail="SearXNG client not initialized")
    
    try:
        logger.info(f"Processing web search with markdown conversion: {search_request.query[:100]}...")
        
        # Perform web search
        search_response = await state.searxng_client.search(
            query=search_request.query,
            categories=search_request.categories,
            language=search_request.language,
            time_range=search_request.time_range,
            page=search_request.page,
            per_page=search_request.per_page,
            bang=search_request.bang
        )
        
        # Get URLs to convert (limited by max_conversions)
        results_to_convert = search_response.results[:search_request.max_conversions]
        urls = [result.url for result in results_to_convert]
        
        logger.info(f"Converting {len(urls)} URLs to markdown...")
        
        # Convert URLs to markdown
        markdown_contents = convert_urls_to_markdown(urls)
        
        # Build markdown results
        markdown_results = []
        converted_count = 0
        failed_count = 0
        
        for i, result in enumerate(results_to_convert):
            markdown_content = markdown_contents[i] if i < len(markdown_contents) else ""
            success = bool(markdown_content)
            
            if success:
                converted_count += 1
            else:
                failed_count += 1
            
            markdown_results.append(MarkdownResult(
                url=result.url,
                title=result.title,
                markdown=markdown_content,
                success=success,
                error=None if success else "Failed to convert URL to markdown"
            ))
        
        logger.info(f"Conversion complete: {converted_count} successful, {failed_count} failed")
        
        return WebSearchMarkdownResponse(
            query=search_response.query,
            search_results_count=len(search_response.results),
            converted_count=converted_count,
            failed_count=failed_count,
            search_results=search_response.results,
            markdown_results=markdown_results,
            page=search_response.page,
            per_page=search_response.per_page
        )
        
    except SearXNGTimeoutError:
        logger.error("SearXNG request timeout")
        raise HTTPException(status_code=504, detail="SearXNG request timeout")
    except SearXNGHTTPError as e:
        logger.error(f"SearXNG HTTP error: {e}")
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except SearXNGConnectionError:
        logger.error("Failed to connect to SearXNG")
        raise HTTPException(status_code=503, detail="SearXNG service unavailable")
    except SearXNGInvalidResponseError as e:
        logger.error(f"SearXNG invalid response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to perform web search with markdown conversion: {e}")
        raise HTTPException(status_code=500, detail=f"Web search with markdown conversion failed: {str(e)}")
