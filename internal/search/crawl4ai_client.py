import logging
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
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

        Raises:
            RuntimeError: If crawler is not initialized
            ValueError: If URL fetch fails
        """
        if not self.crawler:
            raise RuntimeError("Crawler not initialized. Call initialize() first.")

        logger.info(f"Fetching URL: {url}")

        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS
        )

        try:
            result = await self.crawler.arun(url=url, config=run_config)

            if getattr(result, 'success', False):
                markdown = getattr(result, 'markdown', '')
                logger.info(f"Successfully fetched {len(markdown)} characters from {url}")
                return markdown
            else:
                error_msg = getattr(result, 'error_message', 'Unknown error')
                raise ValueError(f"Failed to fetch {url}: {error_msg}")

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()