"""
SearXNG client for web search operations.

Provides methods for:
- General web search with bang syntax
- Specialized category search
- Language prefix handling
- Result parsing and validation
"""

import logging
from typing import Optional, Dict, Any, Literal

import httpx

from internal.config import SearXNGConfig
from .models import (
    SearXNGSearchResponse, 
    SearXNGResult,
    SearchParams,
    SpecializedSearchRequest,
    SpecializedSearchResponse,
    BangResult,
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
    """
    
    def __init__(self, config: SearXNGConfig):
        """
        Initialize the SearXNG client.
        
        Args:
            config: SearXNGConfig with connection settings
        """
        self.config = config
        self.bangs = BangRegistry(config.bangs if hasattr(config, 'bangs') else None)
        
        logger.info(f"Initializing SearXNG client: {config.url}")
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        language: Optional[str] = None,
        time_range: Optional[Literal["day", "week", "month", "year"]] = None,
        page: int = 1,
        per_page: int = 10,
        bang: Optional[str] = None,
        engine: Optional[str] = None
    ) -> SearXNGSearchResponse:
        """
        Perform web search with optional bang syntax.
        
        Args:
            query: Search query string (supports !bangs and :language prefixes)
            category: Search category override
            language: Language code
            time_range: Time filter
            page: Page number
            per_page: Results per page
            bang: Optional bang shortcut to apply
            engine: Specific engine to use
            
        Returns:
            SearXNGSearchResponse with search results
        """
        # Process bang syntax if provided
        bang_result: Optional[BangResult] = None
        if bang:
            bang_result = self.bangs.process_query(f"{bang} {query}")
        elif query.startswith("!"):
            bang_result = self.bangs.process_query(query)
        
        # Build search parameters
        # If a specific engine is set via bang, use it and don't set category
        # to avoid overriding the engine selection
        if bang_result and bang_result.engine:
            params = SearchParams(
                query=bang_result.query if bang_result else query,
                pageno=page,
                language=bang_result.language if bang_result else language,
                time_range=time_range,
                engine=bang_result.engine,
                per_page=per_page
            )
        else:
            params = SearchParams(
                query=bang_result.query if bang_result else query,
                pageno=page,
                categories=category or (bang_result.category if bang_result else None),
                language=bang_result.language if bang_result else language,
                time_range=time_range,
                engine=engine or (bang_result.engine if bang_result else None),
                per_page=per_page
            )
        
        # Make request
        data = await self._make_request(params)
        
        # DEBUG: Log the engine being used
        if bang_result and bang_result.engine:
            logger.debug(f"Bang '{bang}' resolved to engine: '{bang_result.engine}'")
        
        # Parse response
        return self._parse_response(data, page, per_page)
    
    async def search_with_bang(
        self,
        query: str,
        bang: str,
        language: Optional[str] = None,
        time_range: Optional[Literal["day", "week", "month", "year"]] = None,
        page: int = 1,
        per_page: int = 10
    ) -> SearXNGSearchResponse:
        """
        Perform search using bang syntax shortcut.
        
        Args:
            query: Search query string
            bang: Bang shortcut (e.g., '!news', '!gh')
            language: Language code
            time_range: Time filter
            page: Page number
            per_page: Results per page
            
        Returns:
            SearXNGSearchResponse with search results
        """
        return await self.search(
            query=query,
            bang=bang,
            language=language,
            time_range=time_range,
            page=page,
            per_page=per_page
        )
    
    async def search_specialized(
        self,
        request: SpecializedSearchRequest
    ) -> SpecializedSearchResponse:
        """
        Perform search within a specialized category.
        
        Args:
            request: SpecializedSearchRequest with category and query
            
        Returns:
            SpecializedSearchResponse with search results
        """
        response = await self.search(
            query=request.query,
            category=request.category,
            language=request.language,
            time_range=request.time_range,
            page=request.page,
            per_page=request.per_page
        )
        
        # Determine engine from bang
        engine = None
        if request.bang:
            bang_config = self.bangs.get_bang(request.bang)
            engine = bang_config.engine if bang_config else None
        
        return SpecializedSearchResponse(
            query=response.query,
            category=request.category,
            language=request.language,
            results=response.results,
            number_of_results=response.number_of_results,
            engine=engine,
            page=response.page,
            per_page=response.per_page,
            has_next=response.has_next,
            has_previous=response.has_previous
        )
    
    async def get_available_bangs(self) -> Dict[str, Dict[str, Any]]:
        """Get all available bang shortcuts"""
        return self.bangs.get_all_bangs()
    
    async def get_categories(self) -> Dict[str, CategoryInfo]:
        """Get all available search categories"""
        categories = {}
        for bang, config in self.bangs.get_all_bangs().items():
            if config.category:
                if config.category not in categories:
                    categories[config.category] = CategoryInfo(
                        name=config.category,
                        description=f"Search {config.category} content",
                        bang_shortcuts=[]
                    )
                categories[config.category].bang_shortcuts.append(bang)
        return categories
    
    async def _make_request(self, params: SearchParams) -> Dict[str, Any]:
        """Make HTTP request to SearXNG API"""
        url = f"{self.config.url}/search"
        
        request_params = {
            "q": params.query,
            "format": params.format,
            "pageno": params.pageno,
            "per_page": params.per_page
        }
        
        if params.categories:
            request_params["categories"] = params.categories
        if params.language:
            request_params["language"] = params.language
        if params.time_range:
            request_params["time_range"] = params.time_range
        if params.engine:
            request_params["engines"] = params.engine
            logger.debug(f"Setting engine parameter: '{params.engine}'")
        else:
            logger.debug("No engine specified, using default")
        
        # DEBUG: Log the full request parameters
        logger.debug(f"SearXNG request params: {request_params}")
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                logger.debug(f"Making request to: {url}")
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                
                data = response.json()
                raw_results_count = len(data.get('results', []))
                logger.debug(f"Raw SearXNG response: {raw_results_count} results, full data keys: {list(data.keys())}")
                return data
                
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
        page: int, 
        per_page: int
    ) -> SearXNGSearchResponse:
        """Parse SearXNG response into structured format"""
        try:
            results = []
            for result in data.get("results", []):
                results.append(SearXNGResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    engine=result.get("engine", ""),
                    score=result.get("score", 0.0),
                    category=result.get("category", "general")
                ))
            
            # DEBUG: Log engines seen in results
            engines_in_results = set(r.engine for r in results)
            logger.debug(f"Results returned from engines: {engines_in_results}")
            
            has_next = len(results) == per_page
            has_previous = page > 1
            
            return SearXNGSearchResponse(
                query=data.get("query", ""),
                number_of_results=len(results),
                results=results,
                answers=data.get("answers", []),
                infoboxes=data.get("infoboxes", []),
                suggestions=data.get("suggestions", []),
                corrections=data.get("corrections", []),
                page=page,
                per_page=per_page,
                has_next=has_next,
                has_previous=has_previous
            )
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise SearXNGInvalidResponseError(str(e))
