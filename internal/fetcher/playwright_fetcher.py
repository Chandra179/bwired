"""
Browser-based URL fetcher using Playwright (Async API).

Provides browser automation for fetching URLs that are protected by
advanced bot detection systems. Uses a real Chromium browser to make
requests appear as coming from a real user.
"""

import logging
import random
from typing import Optional

from internal.fetcher.config import URLFetcherConfig
from internal.fetcher.constants import (
    USER_AGENTS,
    PLAYWRIGHT_BROWSER_ARGS,
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
)

logger = logging.getLogger(__name__)


class PlaywrightFetcher:
    """
    Browser-based URL fetcher using Playwright (Async API).

    Uses a real browser (Chromium) to fetch URLs, making it much harder
    for bot detection systems to identify as automated.
    """

    def __init__(self, config: URLFetcherConfig):
        """
        Initialize the Playwright fetcher.

        Args:
            config: Configuration object
        """
        self.config = config
        self._playwright = None
        self._browser = None

    async def _ensure_browser(self):
        """Ensure Playwright browser is initialized."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=PLAYWRIGHT_BROWSER_ARGS
                )
                logger.info("Playwright browser initialized")
            except ImportError:
                logger.error(
                    "Playwright not installed. Run: pip install playwright && playwright install chromium"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Playwright browser: {e}")
                raise

    async def fetch(self, url: str) -> str:
        """
        Fetch content from a URL using Playwright browser (async).

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            Exception: If browser automation fails
        """
        await self._ensure_browser()

        context = None
        page = None

        try:
            # Create a new browser context with realistic viewport and locale
            context = await self._browser.new_context(
                viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT},
                user_agent=random.choice(USER_AGENTS),
                locale='en-US',
                timezone_id='America/New_York',
            )

            # Add extra headers to appear more like a real browser
            await context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            })

            page = await context.new_page()

            logger.info(f"Playwright: Navigating to {url}")

            # Navigate to the URL
            response = await page.goto(
                url,
                wait_until=self.config.playwright_wait_until,
                timeout=self.config.playwright_timeout * 1000
            )

            if response is None:
                raise Exception(f"Playwright: No response received from {url}")

            if not response.ok:
                raise Exception(f"Playwright: HTTP {response.status} for {url}")

            # Wait a bit for any dynamic content to load
            await page.wait_for_timeout(2000)

            # Get the page content
            content = await page.content()

            logger.info(
                f"Playwright: Successfully fetched {len(content)} chars from {url}"
            )

            return content

        except Exception as e:
            logger.error(f"Playwright: Failed to fetch {url}: {e}")
            raise

        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def close(self):
        """Close the Playwright browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Playwright browser closed")

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
