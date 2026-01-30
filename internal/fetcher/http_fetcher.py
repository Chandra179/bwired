"""
HTTP-based URL fetcher with retry logic and bot detection handling.

Provides synchronous HTTP fetching using the requests library with
intelligent retry logic, User-Agent rotation, and realistic browser headers.
"""

import logging
import random
import time
from typing import Dict, Optional

import requests

from internal.fetcher.config import URLFetcherConfig
from internal.fetcher.constants import (
    USER_AGENTS,
    BOT_DETECTION_STATUS_CODES,
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
)

logger = logging.getLogger(__name__)


class HTTPFetcher:
    """
    HTTP requests-based URL fetcher with retry logic.

    Features:
    - Rotating User-Agent strings
    - Realistic browser headers
    - Intelligent retry logic with exponential backoff
    - Configurable delays between requests
    """

    def __init__(self, config: URLFetcherConfig):
        """
        Initialize the HTTP fetcher.

        Args:
            config: Configuration object
        """
        self.config = config
        self._session: Optional[requests.Session] = None
        self._last_request_time: Optional[float] = None

    def _get_session(self) -> requests.Session:
        """Get or create a requests session."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _get_random_user_agent(self) -> str:
        """Get a random User-Agent string."""
        return random.choice(USER_AGENTS)

    def _build_headers(self, url: str) -> Dict[str, str]:
        """
        Build realistic browser headers for the request.

        Args:
            url: The URL being requested (used for Referer if applicable)

        Returns:
            Dictionary of HTTP headers
        """
        user_agent = (
            self._get_random_user_agent()
            if self.config.rotate_user_agents
            else USER_AGENTS[0]
        )

        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        return headers

    def _apply_request_delay(self):
        """Apply configured delay between requests."""
        if self.config.request_delay > 0 and self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.config.request_delay:
                sleep_time = self.config.request_delay - elapsed
                logger.debug(f"Applying request delay: {sleep_time:.2f}s")
                time.sleep(sleep_time)
        self._last_request_time = time.time()

    def fetch(self, url: str, timeout: Optional[int] = None) -> str:
        """
        Fetch content using requests library.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            HTML content as string

        Raises:
            requests.RequestException: If request fails after all retries
        """
        timeout = timeout or self.config.timeout
        headers = self._build_headers(url)
        session = self._get_session()

        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Apply request delay if configured
                self._apply_request_delay()

                logger.debug(
                    f"Fetching URL (attempt {attempt + 1}/{self.config.max_retries + 1}): {url}"
                )

                response = session.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True
                )

                # Check for bot detection responses
                if response.status_code in BOT_DETECTION_STATUS_CODES:
                    if attempt < self.config.max_retries:
                        delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                        logger.warning(
                            f"Request blocked with {response.status_code} (attempt {attempt + 1}), "
                            f"retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        # Rotate User-Agent for next attempt
                        if self.config.rotate_user_agents:
                            headers = self._build_headers(url)
                        continue

                response.raise_for_status()

                logger.info(
                    f"Successfully fetched {len(response.text)} chars from {url} "
                    f"(attempt {attempt + 1})"
                )
                return response.text

            except requests.HTTPError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    logger.warning(
                        f"HTTP error {e.response.status_code if e.response else 'unknown'} "
                        f"(attempt {attempt + 1}), retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    raise

            except (requests.Timeout, requests.ConnectionError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    logger.warning(
                        f"{type(e).__name__} (attempt {attempt + 1}), "
                        f"retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    raise

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception
        raise requests.RequestException(f"Failed to fetch {url}")

    def close(self):
        """Close the requests session."""
        if self._session is not None:
            self._session.close()
            self._session = None
            logger.debug("HTTPFetcher session closed")
