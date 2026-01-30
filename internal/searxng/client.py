"""
SearXNG client for web search operations.

This module provides the main SearXNGClient class that handles
communication with the SearXNG search engine, including search
operations, bang syntax processing, and error handling.
"""

import logging
from typing import Optional, Dict, Any, Literal

import httpx

from internal.config import SearXNGConfig
from .models import (
    SearXNGSearchResponse, 
    SearXNGResult,
    SearchParams
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
    
    Provides methods for:
    - General web search
    - Bang syntax processing
    - Result parsing and validation
    - Error handling and retry logic
    
    Attributes:
        config: SearXNGConfig with connection settings
        bangs: BangRegistry for managing bang shortcuts
    """
    
    def __init__(self, config: SearXNGConfig):
        """
        Initialize the SearXNG client.
        
        Args:
            config: SearXNGConfig with connection and behavior settings
        """
        self.config = config
        self.bangs = BangRegistry(config.bangs if hasattr(config, 'bangs') else None)
        
        logger.info(f"Initializing SearXNG client: {config.url}")
        logger.info("SearXNG client loaded successfully")
    
    async def search(
        self,
        query: str,
        categories: Optional[str] = None,
        language: Optional[str] = None,
        time_range: Optional[Literal["day", "week", "month", "year"]] = None,
        page: int = 1,
        per_page: int = 10,
        bang: Optional[str] = None
    ) -> SearXNGSearchResponse:
        """
        Perform web search with optional parameters.
        
        Args:
            query: Search query string
            categories: Search categories (general, news, science, etc.)
            language: Language code (e.g., 'en')
            time_range: Time filter (day, week, month, year)
            page: Page number for pagination
            per_page: Results per page
            bang: Optional bang shortcut to apply
            
        Returns:
            SearXNGSearchResponse with search results
            
        Raises:
            SearXNGTimeoutError: When request times out
            SearXNGConnectionError: When unable to connect
            SearXNGHTTPError: When HTTP error occurs
            SearXNGInvalidResponseError: When response is malformed
        """
        # Process bang syntax if provided
        if bang:
            query = self.bangs.process_query_with_bang(query, bang)
        
        # Build search parameters
        params = SearchParams(
            query=query,
            pageno=page,
            categories=categories,
            language=language,
            time_range=time_range
        )
        
        # Make request
        data = await self._make_request(params)
        
        # Parse response
        return self._parse_response(data, page, per_page)
    
    async def search_with_bang(
        self,
        query: str,
        bang: str,
        categories: Optional[str] = None,
        language: Optional[str] = None,
        time_range: Optional[Literal["day", "week", "month", "year"]] = None,
        page: int = 1,
        per_page: int = 10
    ) -> SearXNGSearchResponse:
        """
        Perform search using bang syntax shortcut.
        
        Args:
            query: Search query string
            bang: Bang shortcut (e.g., '!news', '!go')
            categories: Override category
            language: Language code
            time_range: Time filter
            page: Page number
            per_page: Results per page
            
        Returns:
            SearXNGSearchResponse with search results
        """
        return await self.search(
            query=query,
            categories=categories,
            language=language,
            time_range=time_range,
            page=page,
            per_page=per_page,
            bang=bang
        )
    
    async def get_available_bangs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available bang shortcuts.
        
        Returns:
            Dictionary with bang shortcuts and their configurations
        """
        return self.bangs.get_all_bangs()
    
    async def _make_request(self, params: SearchParams) -> Dict[str, Any]:
        """
        Make HTTP request to SearXNG API.
        
        Args:
            params: Search parameters
            
        Returns:
            Raw response data from SearXNG
            
        Raises:
            SearXNGTimeoutError: When request times out
            SearXNGConnectionError: When unable to connect
            SearXNGHTTPError: When HTTP error occurs
        """
        url = f"{self.config.url}/search"
        
        # Convert to dict for httpx
        request_params = {
            "q": params.query,
            "format": params.format,
            "pageno": params.pageno
        }
        
        if params.categories:
            request_params["categories"] = params.categories
        if params.language:
            request_params["language"] = params.language
        if params.time_range:
            request_params["time_range"] = params.time_range
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                logger.debug(f"Making request to: {url} with params: {request_params}")
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"Received response with {len(data.get('results', []))} results")
                return data
                
        except httpx.TimeoutException:
            logger.error("SearXNG request timeout")
            raise SearXNGTimeoutError()
        except httpx.ConnectError:
            logger.error("Failed to connect to SearXNG")
            raise SearXNGConnectionError()
        except httpx.HTTPStatusError as e:
            logger.error(f"SearXNG HTTP error: {e}")
            raise SearXNGHTTPError(e.response.status_code, f"SearXNG error: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error during SearXNG request: {e}")
            raise
    
    def _parse_response(
        self, 
        data: Dict[str, Any], 
        page: int, 
        per_page: int
    ) -> SearXNGSearchResponse:
        """
        Parse SearXNG response into structured format.
        
        Args:
            data: Raw response data from SearXNG
            page: Current page number
            per_page: Results per page
            
        Returns:
            Parsed SearXNGSearchResponse
            
        Raises:
            SearXNGInvalidResponseError: When response is malformed
        """
        try:
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
            logger.error(f"Failed to parse SearXNG response: {e}")
            raise SearXNGInvalidResponseError(f"Failed to parse response: {str(e)}")