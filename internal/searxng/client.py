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
    CategoryInfo,
    EngineInfo
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
    Supports 4 categories: books, science, social_media, news
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
            request: SearchRequest with query, category, engines, etc.
            
        Returns:
            SearchResponse with results
        """
        # Process bang syntax if present in query
        processed_query = request.query
        engines = request.get_engines()
        category = request.category
        
        if request.query.startswith("!"):
            bang_result = self.bangs.process_query(request.query)
            processed_query = bang_result.query
            if bang_result.engine:
                engines = [bang_result.engine]
            if bang_result.category:
                category = bang_result.category
        
        # Build search parameters
        params = SearchParams(
            query=processed_query,
            pageno=request.page,
            categories=category,
            engines=engines,
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
            Dict of 4 categories: books, science, social_media, news
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
            ),
            "news": CategoryInfo(
                name="news",
                description="Search news articles and current events",
                engines=["duckduckgo news", "presearch news"],
                bang_shortcuts=["!ddn", "!psn"],
                examples=["!ddn technology news", "!psn climate updates"]
            )
        }
    
    async def get_engines(self) -> Dict[str, List[EngineInfo]]:
        """
        Get available search engines grouped by category.
        
        Returns:
            Dict of categories with their engines
        """
        return {
            "books": [
                EngineInfo(name="openlibrary", bang="!ol", description="Search books on OpenLibrary"),
                EngineInfo(name="annas archive", bang="!aa", description="Search books on Anna's Archive")
            ],
            "science": [
                EngineInfo(name="arxiv", bang="!arxiv", description="Search scientific papers on arXiv"),
                EngineInfo(name="google scholar", bang="!gos", description="Search academic papers on Google Scholar")
            ],
            "social_media": [
                EngineInfo(name="reddit", bang="!re", description="Search Reddit discussions")
            ],
            "news": [
                EngineInfo(name="duckduckgo news", bang="!ddn", description="Search news articles on DuckDuckGo"),
                EngineInfo(name="presearch news", bang="!psn", description="Search news articles on Presearch")
            ]
        }
    
    async def _make_request(self, params: SearchParams) -> Dict[str, Any]:
        """Make HTTP request to SearXNG API"""
        url = f"{self.config.url}/search"
        
        request_params = {
            "q": params.query,
            "format": params.format,
            "per_page": params.per_page
        }
        
        # Get engines list (supporting both single and multiple engines)
        engines_list = params.get_engines_list()
        
        # Skip pagination for engines that don't support it (e.g., Reddit)
        if engines_list and any(
            engine.lower() in self.NO_PAGINATION_ENGINES 
            for engine in engines_list
        ):
            logger.debug(f"Skipping pagination for engines - not supported")
        else:
            request_params["pageno"] = params.pageno
        
        if params.categories:
            request_params["categories"] = params.categories
        if params.time_range:
            request_params["time_range"] = params.time_range
        if engines_list:
            # Join multiple engines with comma for SearXNG API
            request_params["engines"] = ",".join(engines_list)
            logger.debug(f"Using engines: '{request_params['engines']}'")
        
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
