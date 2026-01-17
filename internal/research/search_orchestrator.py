import logging
from typing import List, Dict, Any, Optional
import httpx
from internal.config import SearXNGConfig

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """Orchestrate searches using SearXNG API"""

    def __init__(self, config: SearXNGConfig):
        self.config = config
        self.base_url = config.url.rstrip('/')
        logger.info(f"SearchOrchestrator initialized with SearXNG at {self.base_url}")

    def search(
        self,
        query: str,
        engines: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a single search query via SearXNG

        Args:
            query: Search query string
            engines: Optional list of search engines to use
            max_results: Maximum number of results (defaults to config value)

        Returns:
            List of search results with url, title, snippet, and metadata
        """
        if max_results is None:
            max_results = self.config.max_results_per_query

        params = {
            'q': query,
            'format': 'json',
            'pageno': 1,
            'language': 'en'
        }

        if engines:
            params['engines'] = ','.join(engines)

        try:
            logger.info(f"Searching for: {query[:100]}")
            
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.get(
                    f"{self.base_url}/search",
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                results = self._parse_searxng_response(data, query)
                
                logger.info(f"Found {len(results)} results for query: {query[:50]}")
                return results[:max_results]

        except httpx.TimeoutException:
            logger.error(f"Timeout while searching for: {query}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} while searching: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return []

    def search_multiple(
        self,
        queries: List[str],
        max_results_per_query: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Execute multiple search queries in batch

        Args:
            queries: List of search query strings
            max_results_per_query: Max results per query (defaults to config value)

        Returns:
            Dictionary mapping query -> list of search results
        """
        results = {}
        
        for query in queries:
            query_results = self.search(query, max_results=max_results_per_query)
            results[query] = query_results
        
        total_results = sum(len(r) for r in results.values())
        logger.info(f"Completed batch search: {len(queries)} queries, {total_results} total results")
        
        return results

    def _parse_searxng_response(
        self,
        data: Dict[str, Any],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Parse SearXNG JSON response into normalized format

        Args:
            data: Raw SearXNG response JSON
            query: Original query string for logging

        Returns:
            List of normalized search results
        """
        results = []
        
        if 'results' not in data:
            logger.warning(f"No results in SearXNG response for query: {query}")
            return results

        for item in data['results']:
            result = {
                'url': item.get('url', ''),
                'title': item.get('title', ''),
                'snippet': item.get('content', ''),
                'engine': item.get('engine', ''),
                'score': item.get('score', 0),
                'category': item.get('category', ''),
                'parsed_url': item.get('parsed_url', [])
            }
            
            if result['url']:
                results.append(result)
        
        return results

    def get_available_engines(self) -> List[str]:
        """
        Get list of available search engines from SearXNG

        Returns:
            List of engine names
        """
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.get(f"{self.base_url}/config")
                response.raise_for_status()
                data = response.json()
                
                engines = []
                if 'engines' in data:
                    for name, config in data['engines'].items():
                        if config.get('disabled', False) or config.get('inactive', False):
                            continue
                        engines.append(name)
                
                logger.info(f"Found {len(engines)} available engines")
                return engines

        except Exception as e:
            logger.error(f"Failed to get available engines: {e}")
            return []
