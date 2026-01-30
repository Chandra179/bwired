"""
Utility functions for URL fetching.

Provides convenience functions for loading configuration and fetching
URLs with both sync and async interfaces.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import yaml

from internal.fetcher.config import URLFetcherConfig
from internal.fetcher.fetcher import URLFetcher

logger = logging.getLogger(__name__)


def load_fetcher_config(config_path: Optional[Path] = None) -> URLFetcherConfig:
    """
    Load URL fetcher configuration from config.yaml.

    Args:
        config_path: Path to config file. If None, uses default config.yaml.

    Returns:
        URLFetcherConfig object
    """
    if config_path is None:
        config_path = Path("config.yaml")

    # Default configuration
    config = URLFetcherConfig()

    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)

            if yaml_config and 'url_fetching' in yaml_config:
                fetch_config = yaml_config['url_fetching']
                config = URLFetcherConfig(
                    timeout=fetch_config.get('timeout', config.timeout),
                    max_retries=fetch_config.get('max_retries', config.max_retries),
                    retry_delay=fetch_config.get('retry_delay', config.retry_delay),
                    retry_backoff=fetch_config.get('retry_backoff', config.retry_backoff),
                    request_delay=fetch_config.get('request_delay', config.request_delay),
                    rotate_user_agents=fetch_config.get('rotate_user_agents', config.rotate_user_agents),
                    use_playwright_fallback=fetch_config.get('use_playwright_fallback', config.use_playwright_fallback),
                    playwright_timeout=fetch_config.get('playwright_timeout', config.playwright_timeout),
                    playwright_wait_until=fetch_config.get('playwright_wait_until', config.playwright_wait_until),
                )
                logger.info("Loaded URL fetcher configuration from config.yaml")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}. Using defaults.")

    return config


async def fetch_url_content_async(url: str, timeout: Optional[int] = None) -> str:
    """
    Fetch HTML content from a URL using enhanced headers and retry logic (async).

    This is an async convenience function that creates a URLFetcher with configuration
    loaded from config.yaml. Falls back to Playwright for bot-protected sites.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds. If None, uses config timeout.

    Returns:
        HTML content as string

    Raises:
        requests.RequestException: If the request fails
    """
    config = load_fetcher_config()

    async with URLFetcher(config) as fetcher:
        return await fetcher.fetch(url, timeout=timeout)


def fetch_url_content(url: str, timeout: Optional[int] = None) -> str:
    """
    Fetch HTML content from a URL using enhanced headers and retry logic.

    This function handles both sync and async contexts. When called from within an
    async context (like FastAPI), it uses nest_asyncio to allow nested event loops.
    When called from sync context, it uses asyncio.run().

    Falls back to Playwright for bot-protected sites.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds. If None, uses config timeout.

    Returns:
        HTML content as string

    Raises:
        requests.RequestException: If the request fails
    """
    from internal.fetcher.http_fetcher import HTTPFetcher
    from internal.fetcher.playwright_fetcher import PlaywrightFetcher
    import requests

    config = load_fetcher_config()

    # Create HTTP fetcher
    http_fetcher = HTTPFetcher(config)

    try:
        # Try synchronous requests first
        return http_fetcher.fetch(url, timeout=timeout)
    except requests.HTTPError as e:
        # If we got a bot detection error and Playwright fallback is enabled
        if (config.use_playwright_fallback and
            e.response is not None and
            e.response.status_code in [401, 403, 429]):

            logger.warning(
                f"Requests failed with {e.response.status_code}, "
                f"falling back to Playwright browser automation"
            )

            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, use nest_asyncio
                import nest_asyncio
                nest_asyncio.apply()
                # Now we can use asyncio.run even though we're in a loop
                return asyncio.run(_fetch_with_playwright_wrapper(config, url))
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                return asyncio.run(_fetch_with_playwright_wrapper(config, url))
            except ImportError:
                logger.error("nest_asyncio not installed. Run: pip install nest_asyncio")
                raise
            except Exception as playwright_error:
                logger.error(f"Playwright fallback also failed: {playwright_error}")
                raise
        else:
            raise
    finally:
        # Close the HTTP fetcher
        http_fetcher.close()


async def _fetch_with_playwright_wrapper(config: URLFetcherConfig, url: str) -> str:
    """Wrapper to run Playwright fetch and cleanup."""
    from internal.fetcher.playwright_fetcher import PlaywrightFetcher
    
    playwright_fetcher = PlaywrightFetcher(config)
    try:
        return await playwright_fetcher.fetch(url)
    finally:
        await playwright_fetcher.close()
