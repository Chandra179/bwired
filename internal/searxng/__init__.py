"""
SearXNG web search integration components.

This package provides:
- SearXNGClient: Main client for web search operations (requires httpx)
- BangRegistry: Bang shortcuts management
- Data models: Request/response validation models
- Custom exceptions: Specific error handling

Supports 4 categories: books, science, social_media, news

Usage:
    from internal.searxng import SearXNGClient, SearchRequest
    from internal.config import SearXNGConfig
    
    config = SearXNGConfig(url="http://localhost:8888")
    client = SearXNGClient(config)
    
    request = SearchRequest(query="python programming", category="books")
    results = await client.search(request)
"""

from .bangs import BangRegistry
from .models import (
    SearchRequest,
    SearchResponse,
    SearXNGResult,
    BangConfig,
    SearchParams,
    CategoryInfo,
    CategoryListResponse
)
from .exceptions import (
    SearXNGError,
    SearXNGTimeoutError,
    SearXNGConnectionError,
    SearXNGHTTPError,
    SearXNGInvalidResponseError,
    SearXNGBangNotFoundError
)

# Import client separately as it requires httpx
try:
    from .client import SearXNGClient
    _client_available = True
except ImportError:
    SearXNGClient = None
    _client_available = False

__all__ = [
    # Main classes
    'SearXNGClient',
    'BangRegistry',
    
    # Data models
    'SearchRequest',
    'SearchResponse',
    'SearXNGResult',
    'BangConfig',
    'SearchParams',
    'CategoryInfo',
    'CategoryListResponse',
    
    # Exceptions
    'SearXNGError',
    'SearXNGTimeoutError',
    'SearXNGConnectionError',
    'SearXNGHTTPError',
    'SearXNGInvalidResponseError',
    'SearXNGBangNotFoundError',
]
