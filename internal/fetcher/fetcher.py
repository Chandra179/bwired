"""
Main URL fetcher that orchestrates HTTP and Playwright fetchers.

Provides a unified interface for fetching URLs with automatic fallback
to browser automation when bot detection is encountered.
"""

import logging
from typing import Optional

import requests

from internal.fetcher.config import URLFetcherConfig
from internal.fetcher.http_fetcher import HTTPFetcher
from internal.fetcher.playwright_fetcher import PlaywrightFetcher
from internal.fetcher.constants import BOT_DETECTION_STATUS_CODES

logger = logging.getLogger(__name__)


class URLFetcher:
    """
    Enhanced URL fetcher with bot detection bypass capabilities.

    Features:
    - Rotating User-Agent strings
    - Realistic browser headers
    - Intelligent retry logic with exponential backoff
    - Configurable delays between requests
    - Playwright fallback for advanced bot detection

    Example:
        >>> fetcher = URLFetcher()
        >>> content = await fetcher.fetch("https://example.com")
        >>> print(content[:100])
    """

    def __init__(self, config: Optional[URLFetcherConfig] = None):
        """
        Initialize the URL fetcher.

        Args:
            config: Configuration object. If None, uses default configuration.
        """
        self.config = config or URLFetcherConfig()
        self._http_fetcher: Optional[HTTPFetcher] = None
        self._playwright_fetcher: Optional[PlaywrightFetcher] = None

        logger.info(
            f"URLFetcher initialized with timeout={self.config.timeout}s, "
            f"max_retries={self.config.max_retries}, "
            f"playwright_fallback={self.config.use_playwright_fallback}"
        )

    def _get_http_fetcher(self) -> HTTPFetcher:
        """Get or create HTTP fetcher instance."""
        if self._http_fetcher is None:
            self._http_fetcher = HTTPFetcher(self.config)
        return self._http_fetcher

    async def _fetch_with_playwright(self, url: str) -> str:
        """
        Fetch content using Playwright browser automation (async).

        Args:
            url: URL to fetch

        Returns:
            HTML content as string
        """
        if self._playwright_fetcher is None:
            self._playwright_fetcher = PlaywrightFetcher(self.config)

        return await self._playwright_fetcher.fetch(url)

    def _should_fallback_to_playwright(self, error: requests.HTTPError) -> bool:
        """
        Determine if we should fallback to Playwright based on the error.

        Args:
            error: The HTTP error that occurred

        Returns:
            True if Playwright fallback should be attempted
        """
        if not self.config.use_playwright_fallback:
            return False

        if error.response is None:
            return False

        return error.response.status_code in BOT_DETECTION_STATUS_CODES

    async def fetch(self, url: str, timeout: Optional[int] = None) -> str:
        """
        Fetch content from a URL with retry logic and bot detection bypass.

        First tries with requests library, then falls back to Playwright
        if configured and requests fail with bot detection errors.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds. If None, uses config timeout.

        Returns:
            HTML content as string

        Raises:
            requests.RequestException: If all attempts fail
        """
        http_fetcher = self._get_http_fetcher()

        # First try with requests (synchronous)
        try:
            return http_fetcher.fetch(url, timeout=timeout)
        except requests.HTTPError as e:
            # If we got a bot detection error and Playwright fallback is enabled
            if self._should_fallback_to_playwright(e):
                logger.warning(
                    f"Requests failed with {e.response.status_code}, "
                    f"falling back to Playwright browser automation"
                )

                try:
                    return await self._fetch_with_playwright(url)
                except Exception as playwright_error:
                    logger.error(f"Playwright fallback also failed: {playwright_error}")
                    # Re-raise the original error
                    raise
            else:
                # Re-raise if not a bot detection error or fallback disabled
                raise

    async def close(self):
        """Close all fetchers and cleanup resources."""
        if self._http_fetcher is not None:
            self._http_fetcher.close()
            self._http_fetcher = None
            logger.debug("URLFetcher HTTP fetcher closed")

        if self._playwright_fetcher is not None:
            await self._playwright_fetcher.close()
            self._playwright_fetcher = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
