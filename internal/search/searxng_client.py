import logging
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SearXNGClient:
    def __init__(self, api_url: str, timeout: int = 30):
        self.api_url = api_url
        self.timeout = timeout

    async def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Perform a search using SearXNG.

        Args:
            query: Search query string
            num_results: Number of results to return

        Returns:
            List of search results with title, url, snippet
        """
        raise NotImplementedError

    async def _make_request(self, params: Dict) -> Dict:
        """Make HTTP request to SearXNG API"""
        raise NotImplementedError