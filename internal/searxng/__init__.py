"""
SearXNG web search integration components.

This package provides:
- BangRegistry: Configurable bang shortcuts management
- Data models: Request/response validation models
- Custom exceptions: Specific error handling
- SearXNGClient: Main client for web search operations (requires httpx)

Usage:
    from internal.searxng import SearXNGClient
    from internal.config import SearXNGConfig
    
    config = SearXNGConfig(url="http://localhost:8888")
    client = SearXNGClient(config)
    results = await client.search("python programming")
"""

from .bangs import BangRegistry
from .models import (
    SearXNGSearchRequest,
    SearXNGSearchResponse,
    SearXNGResult,
    BangSyntaxRequest,
    BangListResponse,
    BangConfig,
    SearchParams
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
    'SearXNGSearchRequest',
    'SearXNGSearchResponse',
    'SearXNGResult',
    'BangSyntaxRequest',
    'BangListResponse',
    'BangConfig',
    'SearchParams',
    
    # Exceptions
    'SearXNGError',
    'SearXNGTimeoutError',
    'SearXNGConnectionError',
    'SearXNGHTTPError',
    'SearXNGInvalidResponseError',
    'SearXNGBangNotFoundError',
]