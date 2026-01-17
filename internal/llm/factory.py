"""Factory for creating LLM clients based on configuration."""

import logging

from internal.config import LLMProviderConfig
from .base import LLMClient
from .ollama import OllamaClient
from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)


def create_llm_client(config: LLMProviderConfig) -> LLMClient:
    """
    Create an LLM client based on the provider configuration.
    
    Args:
        config: LLM provider configuration specifying which provider to use
        
    Returns:
        Configured LLM client instance
        
    Raises:
        ValueError: If provider is not supported
    """
    provider = config.provider.lower()
    
    if provider == "ollama":
        logger.info(f"Creating Ollama client with model: {config.ollama.model}")
        return OllamaClient(config.ollama)
    
    elif provider == "openai":
        logger.info(f"Creating OpenAI client with model: {config.openai.model}")
        return OpenAIClient(config.openai)
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported: ollama, openai")
