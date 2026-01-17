"""Common error handling utilities for research endpoints."""
import logging
from typing import Optional, Dict, Any, NoReturn

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def handle_not_found(resource_type: str, identifier: str) -> NoReturn:
    """Raise 404 Not Found exception with consistent format."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource_type} '{identifier}' not found"
    )


def handle_validation_error(message: str) -> NoReturn:
    """Raise 400 Bad Request exception for validation errors."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Validation error: {message}"
    )


def log_and_raise_internal_error(context: str, error: Exception) -> NoReturn:
    """Log error and raise 500 Internal Server Error."""
    logger.error(f"{context}: {error}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {context.lower()}: {str(error)}"
    )


class SessionNotFoundError(Exception):
    """Raised when a research session is not found."""


class TemplateNotFoundError(Exception):
    """Raised when a template is not found."""


class ServiceNotInitializedError(Exception):
    """Raised when a required service is not initialized."""
