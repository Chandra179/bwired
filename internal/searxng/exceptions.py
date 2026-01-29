"""
Custom exceptions for SearXNG web search integration.

This module defines specific exceptions that can be raised by the SearXNG client
to provide better error handling and user feedback.
"""


class SearXNGError(Exception):
    """Base exception for all SearXNG-related errors"""
    pass


class SearXNGTimeoutError(SearXNGError):
    """Raised when a request to SearXNG times out"""
    def __init__(self, message: str = "SearXNG request timeout"):
        super().__init__(message)


class SearXNGConnectionError(SearXNGError):
    """Raised when unable to connect to SearXNG service"""
    def __init__(self, message: str = "Failed to connect to SearXNG"):
        super().__init__(message)


class SearXNGHTTPError(SearXNGError):
    """Raised when SearXNG returns an HTTP error status"""
    def __init__(self, status_code: int, message: str = "SearXNG HTTP error"):
        self.status_code = status_code
        super().__init__(f"{message}: {status_code}")


class SearXNGInvalidResponseError(SearXNGError):
    """Raised when SearXNG returns invalid or malformed response"""
    def __init__(self, message: str = "Invalid response from SearXNG"):
        super().__init__(message)


class SearXNGBangNotFoundError(SearXNGError):
    """Raised when a requested bang shortcut is not found"""
    def __init__(self, bang: str):
        super().__init__(f"Bang shortcut not found: {bang}")
        self.bang = bang