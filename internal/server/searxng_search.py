import logging
from typing import List, Optional, Dict, Any, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)
router = APIRouter()

class SearXNGSearchRequest(BaseModel):
    query: str
    categories: Optional[str] = Field("general", description="general, news, science, images, videos, files, it, map")
    language: Optional[str] = Field("en", description="Language code")
    time_range: Optional[Literal["day", "week", "month", "year"]] = None
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination")
    per_page: Optional[int] = Field(10, ge=1, le=1000, description="Results per page (max 1000)")
    bang: Optional[str] = Field(None, description="Bang shortcut (e.g., '!news', '!go', '!yhn')")

class BangSyntaxRequest(BaseModel):
    query: str
    bang: str = Field(..., description="Bang shortcut (e.g., '!news', '!go', '!yhn')")
    categories: Optional[str] = Field(None, description="Override category")
    language: Optional[str] = Field("en", description="Language code")
    time_range: Optional[Literal["day", "week", "month", "year"]] = None
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination")
    per_page: Optional[int] = Field(10, ge=1, le=1000, description="Results per page (max 1000)")

class BangListResponse(BaseModel):
    available_bangs: Dict[str, Dict[str, Any]]

class SearXNGResult(BaseModel):
    title: str
    url: str
    content: str
    engine: str
    score: float
    category: str

class SearXNGSearchResponse(BaseModel):
    query: str
    number_of_results: int
    results: List[SearXNGResult]
    answers: List[Dict[str, Any]]
    infoboxes: List[Dict[str, Any]]
    suggestions: List[str]
    corrections: List[str]
    page: int
    per_page: int
    has_next: bool
    has_previous: bool

@router.post("/web-search", response_model=SearXNGSearchResponse)
async def web_search(request: SearXNGSearchRequest):
    """
    Search the web using SearXNG API
    """
    searxng_url = "http://localhost:8888/search"
    
    params = {
        "q": request.query,
        "format": "json",
        "pageno": request.page
    }
    
    if request.categories:
        params["categories"] = request.categories
    if request.language:
        params["language"] = request.language
    if request.time_range:
        params["time_range"] = request.time_range
    
    # Apply bang syntax if provided
    if request.bang:
        params["q"] = f"{request.bang} {request.query}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(searxng_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            results = []
            for result in data.get("results", []):
                results.append(SearXNGResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    engine=result.get("engine", ""),
                    score=result.get("score", 0.0),
                    category=result.get("category", "")
                ))
            
            # Calculate pagination metadata
            current_page = request.page or 1
            per_page = request.per_page or 10
            has_next = len(results) == per_page
            has_previous = current_page > 1

            return SearXNGSearchResponse(
                query=data.get("query", request.query),
                number_of_results=len(results),
                results=results,
                answers=data.get("answers", []),
                infoboxes=data.get("infoboxes", []),
                suggestions=data.get("suggestions", []),
                corrections=data.get("corrections", []),
                page=current_page,
                per_page=per_page,
                has_next=has_next,
                has_previous=has_previous
            )
            
    except httpx.TimeoutException:
        logger.error("SearXNG request timeout")
        raise HTTPException(status_code=504, detail="SearXNG request timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"SearXNG HTTP error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"SearXNG error: {e.response.text}")
    except httpx.ConnectError:
        logger.error("Failed to connect to SearXNG")
        raise HTTPException(status_code=503, detail="SearXNG service unavailable")
    except Exception as e:
        logger.error(f"Failed to perform web search: {e}")
        raise HTTPException(status_code=500, detail=f"Web search failed: {str(e)}")

@router.post("/web-search/bang", response_model=SearXNGSearchResponse)
async def web_search_with_bang(request: BangSyntaxRequest):
    """
    Search using bang syntax shortcuts
    """
    searxng_url = "http://localhost:8888/search"
    
    # Combine bang and query
    query = f"{request.bang} {request.query}"
    
    # Special handling for reddit bang to enforce site-specific search
    if request.bang == "!re":
        query = f"site:reddit.com {request.query}"
        logger.info(f"Reddit bang detected - transformed query to: {query}")
    
    params = {
        "q": query,
        "format": "json",
        "pageno": request.page
    }
    
    if request.categories:
        params["categories"] = request.categories
    if request.language:
        params["language"] = request.language
    if request.time_range:
        params["time_range"] = request.time_range
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(searxng_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            results = []
            for result in data.get("results", []):
                results.append(SearXNGResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    engine=result.get("engine", ""),
                    score=result.get("score", 0.0),
                    category=result.get("category", "")
                ))
            
            # Calculate pagination metadata
            current_page = request.page or 1
            per_page = request.per_page or 10
            has_next = len(results) == per_page
            has_previous = current_page > 1

            return SearXNGSearchResponse(
                query=data.get("query", query),
                number_of_results=len(results),
                results=results,
                answers=data.get("answers", []),
                infoboxes=data.get("infoboxes", []),
                suggestions=data.get("suggestions", []),
                corrections=data.get("corrections", []),
                page=current_page,
                per_page=per_page,
                has_next=has_next,
                has_previous=has_previous
            )
            
    except httpx.TimeoutException:
        logger.error("SearXNG request timeout")
        raise HTTPException(status_code=504, detail="SearXNG request timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"SearXNG HTTP error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"SearXNG error: {e.response.text}")
    except httpx.ConnectError:
        logger.error("Failed to connect to SearXNG")
        raise HTTPException(status_code=503, detail="SearXNG service unavailable")
    except Exception as e:
        logger.error(f"Failed to perform web search: {e}")
        raise HTTPException(status_code=500, detail=f"Web search failed: {str(e)}")

@router.get("/web-search/bangs", response_model=BangListResponse)
async def get_available_bangs():
    """
    Get list of available bang shortcuts and their descriptions
    """
    available_bangs = {
        # Categories
        "!news": {
            "name": "All News Engines",
            "description": "Search all enabled news sources",
            "engines": ["Google News", "Bing News", "Yahoo News", "DuckDuckGo News", "Qwant News", "Reddit", "Twitter"]
        },
        "!images": {
            "name": "All Images",
            "description": "Search all image sources",
            "engines": ["Google Images", "Bing Images", "DuckDuckGo Images", "Qwant Images"]
        },
        "!videos": {
            "name": "All Videos", 
            "description": "Search all video sources",
            "engines": ["YouTube", "Google Videos", "Bing Videos", "DuckDuckGo Videos"]
        },
        "!map": {
            "name": "Maps",
            "description": "Search maps and locations",
            "engines": ["OpenStreetMap"]
        },
        
        # News Engines
        "!yhn": {
            "name": "Yahoo News",
            "description": "Search Yahoo News specifically",
            "category": "news"
        },
        "!ddn": {
            "name": "DuckDuckGo News",
            "description": "Search DuckDuckGo News specifically", 
            "category": "news"
        },
        "!qwn": {
            "name": "Qwant News",
            "description": "Search Qwant News specifically",
            "category": "news"
        },
        
        # General Search Engines
        "!go": {
            "name": "Google",
            "description": "Search Google specifically",
            "categories": ["general", "news"]
        },
        "!bi": {
            "name": "Bing",
            "description": "Search Bing specifically",
            "categories": ["general", "news"]
        },
        "!br": {
            "name": "Brave",
            "description": "Search Brave specifically",
            "categories": ["general", "news"]
        },
        "!re": {
            "name": "Reddit",
            "description": "Search Reddit (custom Google search)",
            "categories": ["news", "general"]
        }
    }
    
    return BangListResponse(available_bangs=available_bangs)