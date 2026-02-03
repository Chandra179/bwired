"""
SearXNG client for web search operations.

Provides methods for:
- Unified search across books, science, and social media
- Category-based search
- Bang syntax handling
- Result parsing and validation
"""

import logging
from typing import Optional, Dict, Any, List

import httpx

from internal.config import SearXNGConfig
from .models import (
    SearchResponse, 
    SearXNGResult,
    SearchParams,
    SearchRequest,
    CategoryInfo
)
from .bangs import BangRegistry
from .exceptions import (
    SearXNGTimeoutError,
    SearXNGConnectionError,
    SearXNGHTTPError,
    SearXNGInvalidResponseError
)

logger = logging.getLogger(__name__)


class SearXNGClient:
    """
    Client for SearXNG web search operations.
    Supports 3 categories: books, science, social_media
    """
    
    # Engines that don't support pagination
    NO_PAGINATION_ENGINES = ["reddit"]
    
    def __init__(self, config: SearXNGConfig):
        """
        Initialize the SearXNG client.
        
        Args:
            config: SearXNGConfig with connection settings
        """
        self.config = config
        self.bangs = BangRegistry()
        
        logger.info(f"Initializing SearXNG client: {config.url}")
    
    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform unified search across all categories.
        
        Args:
            request: SearchRequest with query, category, engine, etc.
            
        Returns:
            SearchResponse with results
        """
        # Process bang syntax if present in query
        processed_query = request.query
        engine = request.engine
        category = request.category
        
        if request.query.startswith("!"):
            bang_result = self.bangs.process_query(request.query)
            processed_query = bang_result.query
            if bang_result.engine:
                engine = bang_result.engine
            if bang_result.category:
                category = bang_result.category
        
        # Build search parameters
        params = SearchParams(
            query=processed_query,
            pageno=request.page,
            categories=category,
            engine=engine,
            time_range=request.time_range,
            per_page=request.per_page
        )
        
        # Make request
        data = await self._make_request(params)
        
        # Parse response
        return self._parse_response(data, params)
    
    async def get_categories(self) -> Dict[str, CategoryInfo]:
        """
        Get available search categories with engines and bangs.
        
        Returns:
            Dict of 3 categories: books, science, social_media
        """
        return {
            "books": CategoryInfo(
                name="books",
                description="Search books and literature",
                engines=["openlibrary", "annas archive"],
                bang_shortcuts=["!ol", "!aa"],
                examples=["!ol python programming", "!aa machine learning"]
            ),
            "science": CategoryInfo(
                name="science",
                description="Search scientific papers and academic content",
                engines=["arxiv", "google scholar"],
                bang_shortcuts=["!arxiv", "!gos"],
                examples=["!arxiv quantum computing", "!gos climate change"]
            ),
            "social_media": CategoryInfo(
                name="social_media",
                description="Search social media discussions",
                engines=["reddit"],
                bang_shortcuts=["!re"],
                examples=["!re web development"]
            )
        }
    
    async def _make_request(self, params: SearchParams) -> Dict[str, Any]:
        """Make HTTP request to SearXNG API"""
        url = f"{self.config.url}/search"
        
        request_params = {
            "q": params.query,
            "format": params.format,
            "per_page": params.per_page
        }
        
        # Skip pagination for engines that don't support it (e.g., Reddit)
        if params.engine and params.engine.lower() in self.NO_PAGINATION_ENGINES:
            logger.debug(f"Skipping pagination for {params.engine} - not supported")
        else:
            request_params["pageno"] = params.pageno
        
        if params.categories:
            request_params["categories"] = params.categories
        if params.time_range:
            request_params["time_range"] = params.time_range
        if params.engine:
            request_params["engines"] = params.engine
            logger.debug(f"Using engine: '{params.engine}'")
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error("SearXNG request timeout")
            raise SearXNGTimeoutError()
        except httpx.ConnectError:
            logger.error("Failed to connect to SearXNG")
            raise SearXNGConnectionError()
        except httpx.HTTPStatusError as e:
            logger.error(f"SearXNG HTTP error: {e}")
            raise SearXNGHTTPError(e.response.status_code, str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    
    def _parse_response(
        self, 
        data: Dict[str, Any], 
        params: SearchParams
    ) -> SearchResponse:
        """Parse SearXNG response into unified format"""
        try:
            results = []
            for result in data.get("results", []):
                results.append(SearXNGResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    engine=result.get("engine", ""),
                    score=result.get("score", 0.0),
                    category=result.get("category", params.categories or "general")
                ))
            
            # Determine if there's a next page
            # For engines without pagination, has_next is always False
            if params.engine and params.engine.lower() in self.NO_PAGINATION_ENGINES:
                has_next = False
            else:
                has_next = len(results) == params.per_page
            
            has_previous = params.pageno > 1
            
            return SearchResponse(
                query=data.get("query", params.query),
                category=params.categories,
                engine=params.engine,
                results=results,
                number_of_results=len(results),
                page=params.pageno,
                per_page=params.per_page,
                has_next=has_next,
                has_previous=has_previous
            )
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise SearXNGInvalidResponseError(str(e))
