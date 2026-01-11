import logging
from crawl4ai import AsyncWebCrawler
from typing import Optional

logger = logging.getLogger(__name__)


class Crawl4AIClient:
    def __init__(self, browser_type: str = "chromium", headless: bool = True, timeout: int = 30):
        self.browser_type = browser_type
        self.headless = headless
        self.timeout = timeout
        self.crawler: Optional[AsyncWebCrawler] = None

    async def initialize(self):
        """Initialize the crawler"""
        self.crawler = AsyncWebCrawler(
            browser_type=self.browser_type,
            headless=self.headless,
        )
        await self.crawler.start()

    async def close(self):
        """Close the crawler"""
        if self.crawler:
            await self.crawler.close()

    async def fetch_url(self, url: str) -> str:
        """
        Fetch URL and return markdown content.

        Args:
            url: URL to crawl

        Returns:
            Markdown content as string
        """
        raise NotImplementedError