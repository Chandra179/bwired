"""
Configuration for URL fetching behavior.

Provides the URLFetcherConfig dataclass with validation for all
fetching parameters including timeouts, retries, and feature toggles.
"""

from dataclasses import dataclass

from internal.fetcher.constants import (
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_RETRY_BACKOFF,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_PLAYWRIGHT_TIMEOUT,
    DEFAULT_PLAYWRIGHT_WAIT_UNTIL,
)


@dataclass
class URLFetcherConfig:
    """Configuration for URL fetching behavior."""

    timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY
    retry_backoff: float = DEFAULT_RETRY_BACKOFF
    request_delay: float = DEFAULT_REQUEST_DELAY
    rotate_user_agents: bool = True
    use_playwright_fallback: bool = True
    playwright_timeout: int = DEFAULT_PLAYWRIGHT_TIMEOUT
    playwright_wait_until: str = DEFAULT_PLAYWRIGHT_WAIT_UNTIL

    def __post_init__(self):
        """Validate configuration values."""
        if self.timeout < 1:
            raise ValueError("timeout must be at least 1 second")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay cannot be negative")
        if self.retry_backoff < 1.0:
            raise ValueError("retry_backoff must be at least 1.0")
