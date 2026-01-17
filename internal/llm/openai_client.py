"""OpenAI LLM client using Instructor for structured extraction."""

import asyncio
from typing import Type, TypeVar
from pydantic import BaseModel
import instructor
from openai import AsyncOpenAI
import logging

from internal.config import OpenAILLMConfig
from .base import LLMClient, ExtractionResult

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class OpenAIClient(LLMClient):
    """
    LLM client for OpenAI API using Instructor.
    
    Supports both OpenAI's official API and compatible endpoints.
    """
    
    def __init__(self, config: OpenAILLMConfig):
        """
        Initialize OpenAI client.
        
        Args:
            config: OpenAI configuration with api_key and model
        """
        self.config = config
        self.model = config.model
        
        client_kwargs = {
            "api_key": config.api_key,
            "timeout": config.timeout
        }
        
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        
        # Create OpenAI client
        self._openai_client = AsyncOpenAI(**client_kwargs)
        
        # Patch with Instructor for structured outputs
        self._client = instructor.from_openai(self._openai_client)
        
        logger.info(f"Initialized OpenAI client with model {self.model}")
    
    async def extract_structured(
        self,
        content: str,
        output_model: Type[T],
        system_prompt: str,
        max_retries: int = 2
    ) -> ExtractionResult[T]:
        """
        Extract structured data from content using Instructor.
        
        Args:
            content: The text content to extract from
            output_model: Pydantic model class for output structure
            system_prompt: System prompt for extraction guidance
            max_retries: Number of retries on validation failure
            
        Returns:
            ExtractionResult with parsed data or error
        """
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract structured information from the following content:\n\n{content}"}
                ],
                response_model=output_model,
                max_retries=max_retries
            )
            
            # OpenAI models generally have higher reliability
            confidence = 0.90
            
            return ExtractionResult(
                success=True,
                data=response,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return ExtractionResult(
                success=False,
                error=str(e),
                confidence=0.0
            )
    
    async def extract_batch(
        self,
        contents: list[str],
        output_model: Type[T],
        system_prompt: str,
        max_retries: int = 2
    ) -> list[ExtractionResult[T]]:
        """
        Extract structured data from multiple content pieces concurrently.
        
        Args:
            contents: List of text contents
            output_model: Pydantic model for output structure
            system_prompt: System prompt for extraction
            max_retries: Retries per extraction
            
        Returns:
            List of ExtractionResults
        """
        tasks = [
            self.extract_structured(content, output_model, system_prompt, max_retries)
            for content in contents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(ExtractionResult(
                    success=False,
                    error=str(result),
                    confidence=0.0
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_model_name(self) -> str:
        return self.model
    
    def get_provider_name(self) -> str:
        return "openai"
