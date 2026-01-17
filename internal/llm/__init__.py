"""LLM client abstraction layer for structured extraction."""

from .base import LLMClient, ExtractionResult
from .ollama import OllamaClient
from .openai_client import OpenAIClient
from .factory import create_llm_client

__all__ = [
    "LLMClient",
    "ExtractionResult",
    "OllamaClient",
    "OpenAIClient",
    "create_llm_client",
]
