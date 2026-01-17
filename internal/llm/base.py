"""Base LLM client interface for structured extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Type, TypeVar, Generic, Optional, Any, Dict
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


@dataclass
class ExtractionResult(Generic[T]):
    """Result from structured extraction."""
    success: bool
    data: Optional[T] = None
    confidence: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None


class LLMClient(ABC):
    """
    Abstract base class for LLM clients that support structured extraction.
    
    All implementations use Instructor for structured output parsing,
    which works with OpenAI-compatible APIs including Ollama.
    """
    
    @abstractmethod
    async def extract_structured(
        self,
        content: str,
        output_model: Type[T],
        system_prompt: str,
        max_retries: int = 2
    ) -> ExtractionResult[T]:
        """
        Extract structured data from content using the specified Pydantic model.
        
        Args:
            content: The text content to extract from
            output_model: Pydantic model class defining the expected structure
            system_prompt: System prompt guiding the extraction
            max_retries: Number of retries on validation failure
            
        Returns:
            ExtractionResult containing the parsed data or error info
        """
        pass
    
    @abstractmethod
    async def extract_batch(
        self,
        contents: list[str],
        output_model: Type[T],
        system_prompt: str,
        max_retries: int = 2
    ) -> list[ExtractionResult[T]]:
        """
        Extract structured data from multiple content pieces.
        
        Args:
            contents: List of text contents to extract from
            output_model: Pydantic model class defining the expected structure
            system_prompt: System prompt guiding the extraction
            max_retries: Number of retries on validation failure
            
        Returns:
            List of ExtractionResults
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the underlying model."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of the provider (e.g., 'ollama', 'openai')."""
        pass
