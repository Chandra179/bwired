"""
URL fetching package with bot detection bypass capabilities.

Provides enhanced HTTP requests with rotating User-Agents, realistic browser headers,
and intelligent retry logic to avoid bot detection. Falls back to Playwright browser
automation for advanced bot protection systems.

Example:
    >>> from internal.fetcher import URLFetcher, fetch_url_content
    >>>
    >>> # Using the async fetcher class
    >>> async with URLFetcher() as fetcher:
    ...     content = await fetcher.fetch("https://example.com")
    ...
    >>> # Using the sync convenience function
    >>> content = fetch_url_content("https://example.com")
"""

from internal.fetcher.constants import USER_AGENTS
from internal.fetcher.config import URLFetcherConfig
from internal.fetcher.http_fetcher import HTTPFetcher
from internal.fetcher.playwright_fetcher import PlaywrightFetcher
from internal.fetcher.fetcher import URLFetcher
from internal.fetcher.utils import (
    load_fetcher_config,
    fetch_url_content_async,
    fetch_url_content,
)

__all__ = [
    # Configuration
    "URLFetcherConfig",
    # Fetcher classes
    "URLFetcher",
    "HTTPFetcher",
    "PlaywrightFetcher",
    # Utility functions
    "fetch_url_content",
    "fetch_url_content_async",
    "load_fetcher_config",
    # Constants
    "USER_AGENTS",
]
