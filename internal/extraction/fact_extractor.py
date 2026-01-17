"""
Fact extractor for structured data extraction from research chunks.

Uses LLM with Instructor to extract facts according to template schemas.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
import logging

from internal.config import ExtractionConfig
from internal.research.models import ResearchTemplate
from internal.extraction.schema_builder import build_pydantic_model, validate_schema_for_extraction
from internal.llm import LLMClient, ExtractionResult, create_llm_client
from internal.storage.postgres_client import PostgresClient

logger = logging.getLogger(__name__)


@dataclass
class ChunkWithMetadata:
    """Chunk data with associated metadata for extraction."""
    chunk_id: str
    content: str
    source_url: str
    seed_question: Optional[str] = None
    section_path: Optional[str] = None


@dataclass
class ExtractedFact:
    """A single extracted fact with metadata."""
    chunk_id: str
    source_url: str
    seed_question: Optional[str]
    fact_data: Dict[str, Any]
    confidence: float
    extraction_notes: Optional[str] = None


@dataclass
class ExtractionProgress:
    """Tracks extraction progress for a session."""
    session_id: str
    total_chunks: int
    processed_chunks: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    
    @property
    def completion_rate(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return self.processed_chunks / self.total_chunks
    
    @property
    def success_rate(self) -> float:
        if self.processed_chunks == 0:
            return 0.0
        return self.successful_extractions / self.processed_chunks


class FactExtractor:
    """
    Extracts structured facts from text chunks using LLM.
    
    Uses template schemas to define expected output structure,
    and Instructor for reliable structured extraction.
    """
    
    def __init__(
        self,
        config: ExtractionConfig,
        postgres_client: PostgresClient
    ):
        """
        Initialize the fact extractor.
        
        Args:
            config: Extraction configuration with LLM settings
            postgres_client: Database client for storing facts
        """
        self.config = config
        self.postgres_client = postgres_client
        self.llm_client = create_llm_client(config.llm)
        
        logger.info(
            f"Initialized FactExtractor with {self.llm_client.get_provider_name()} "
            f"model: {self.llm_client.get_model_name()}"
        )
    
    async def extract_from_chunk(
        self,
        chunk: ChunkWithMetadata,
        template: ResearchTemplate
    ) -> Optional[ExtractedFact]:
        """
        Extract structured data from a single chunk.
        
        Args:
            chunk: The chunk to extract from
            template: Research template defining expected structure
            
        Returns:
            ExtractedFact if successful, None if extraction failed
        """
        # Validate schema first
        errors = validate_schema_for_extraction(template.schema_json)
        if errors:
            logger.error(f"Invalid template schema: {errors}")
            return None
        
        # Build dynamic Pydantic model from template
        output_model = build_pydantic_model(template.schema_json, "ExtractedData")
        
        # Prepare system prompt
        system_prompt = self._build_system_prompt(template)
        
        # Extract using LLM
        result = await self.llm_client.extract_structured(
            content=chunk.content,
            output_model=output_model,
            system_prompt=system_prompt
        )
        
        if result.success and result.data:
            return ExtractedFact(
                chunk_id=chunk.chunk_id,
                source_url=chunk.source_url,
                seed_question=chunk.seed_question,
                fact_data=result.data.model_dump(),
                confidence=result.confidence
            )
        else:
            logger.warning(f"Extraction failed for chunk {chunk.chunk_id}: {result.error}")
            return None
    
    async def extract_batch(
        self,
        chunks: List[ChunkWithMetadata],
        template: ResearchTemplate,
        session_id: str
    ) -> ExtractionProgress:
        """
        Extract facts from multiple chunks with batch processing.
        
        Args:
            chunks: List of chunks to process
            template: Research template for extraction
            session_id: Research session ID for storing results
            
        Returns:
            ExtractionProgress with statistics
        """
        progress = ExtractionProgress(
            session_id=session_id,
            total_chunks=len(chunks)
        )
        
        # Validate schema once
        errors = validate_schema_for_extraction(template.schema_json)
        if errors:
            logger.error(f"Invalid template schema: {errors}")
            progress.failed_extractions = len(chunks)
            return progress
        
        # Build the model once for all extractions
        output_model = build_pydantic_model(template.schema_json, "ExtractedData")
        system_prompt = self._build_system_prompt(template)
        
        # Process in batches
        batch_size = self.config.batch_size
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Extract from batch concurrently
            tasks = [
                self._extract_single(
                    chunk=chunk,
                    output_model=output_model,
                    system_prompt=system_prompt,
                    session_id=session_id
                )
                for chunk in batch
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                progress.processed_chunks += 1
                
                if isinstance(result, Exception):
                    logger.error(f"Extraction error: {result}")
                    progress.failed_extractions += 1
                elif result is not None:
                    progress.successful_extractions += 1
                else:
                    progress.failed_extractions += 1
            
            # Update session progress periodically
            if i % (batch_size * 2) == 0:
                self._update_session_progress(session_id, progress)
        
        # Final progress update
        self._update_session_progress(session_id, progress)
        
        logger.info(
            f"Extraction complete for session {session_id}: "
            f"{progress.successful_extractions}/{progress.total_chunks} successful"
        )
        
        return progress
    
    async def _extract_single(
        self,
        chunk: ChunkWithMetadata,
        output_model: Type[BaseModel],
        system_prompt: str,
        session_id: str
    ) -> Optional[ExtractedFact]:
        """
        Extract from a single chunk and store the result.
        
        Args:
            chunk: Chunk to extract from
            output_model: Pydantic model for extraction
            system_prompt: System prompt for LLM
            session_id: Session ID for storage
            
        Returns:
            ExtractedFact if successful
        """
        try:
            result = await self.llm_client.extract_structured(
                content=chunk.content,
                output_model=output_model,
                system_prompt=system_prompt
            )
            
            if result.success and result.data:
                # Check confidence threshold
                if result.confidence >= self.config.confidence_threshold:
                    fact = ExtractedFact(
                        chunk_id=chunk.chunk_id,
                        source_url=chunk.source_url,
                        seed_question=chunk.seed_question,
                        fact_data=result.data.model_dump(),
                        confidence=result.confidence
                    )
                    
                    # Store fact in database
                    self._store_fact(session_id, fact)
                    
                    return fact
                else:
                    logger.debug(
                        f"Extraction below confidence threshold "
                        f"({result.confidence} < {self.config.confidence_threshold})"
                    )
                    return None
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting from chunk {chunk.chunk_id}: {e}")
            raise
    
    def _build_system_prompt(self, template: ResearchTemplate) -> str:
        """
        Build the system prompt for extraction.
        
        Args:
            template: Research template with optional custom prompt
            
        Returns:
            Complete system prompt for the LLM
        """
        base_prompt = template.system_prompt or (
            "You are an expert information extractor. "
            "Extract structured data from the provided content accurately and completely. "
            "Only include information that is explicitly stated in the content. "
            "Do not make assumptions or add information not present in the source."
        )
        
        # Add schema context
        schema_context = self._format_schema_for_prompt(template.schema_json)
        
        full_prompt = f"""{base_prompt}

You will extract information according to the following schema:
{schema_context}

Guidelines:
1. Only extract information explicitly present in the content
2. Leave fields empty/null if information is not available
3. Be precise with dates, numbers, and proper nouns
4. For arrays, include all relevant items found
5. Maintain factual accuracy - do not infer or assume"""

        return full_prompt
    
    def _format_schema_for_prompt(self, schema: Dict[str, Any]) -> str:
        """Format schema as readable text for the prompt."""
        fields = schema.get("fields", {})
        lines = []
        
        for name, field_def in fields.items():
            field_type = field_def.get("type", "string")
            description = field_def.get("description", "")
            required = field_def.get("required", True)
            
            req_marker = "(required)" if required else "(optional)"
            lines.append(f"- {name} ({field_type}) {req_marker}: {description}")
        
        return "\n".join(lines)
    
    def _store_fact(self, session_id: str, fact: ExtractedFact) -> str:
        """
        Store an extracted fact in the database.
        
        Args:
            session_id: Research session ID
            fact: Extracted fact to store
            
        Returns:
            ID of the stored fact
        """
        return self.postgres_client.store_fact(
            session_id=session_id,
            chunk_id=fact.chunk_id,
            source_url=fact.source_url,
            fact_data=fact.fact_data,
            confidence=fact.confidence,
            seed_question=fact.seed_question
        )
    
    def _update_session_progress(
        self,
        session_id: str,
        progress: ExtractionProgress
    ) -> None:
        """Update session with extraction progress."""
        progress_data = {
            "extraction_total": progress.total_chunks,
            "extraction_processed": progress.processed_chunks,
            "extraction_successful": progress.successful_extractions,
            "extraction_failed": progress.failed_extractions,
            "extraction_completion_rate": progress.completion_rate,
            "extraction_success_rate": progress.success_rate
        }
        
        self.postgres_client.update_session_status(
            session_id=session_id,
            status="extracting",
            progress=progress_data
        )
    
    def validate_extraction(
        self,
        fact: ExtractedFact,
        original_content: str
    ) -> bool:
        """
        Validate that extracted facts are grounded in the source content.
        
        This is a basic validation that checks if key terms from the
        extracted data appear in the source content.
        
        Args:
            fact: The extracted fact
            original_content: The original chunk content
            
        Returns:
            True if validation passes
        """
        content_lower = original_content.lower()
        
        # Check if key values from fact appear in content
        for key, value in fact.fact_data.items():
            if isinstance(value, str) and len(value) > 3:
                # Check if significant strings appear in content
                # This is a simple heuristic - more sophisticated validation
                # could use semantic similarity
                words = value.lower().split()
                significant_words = [w for w in words if len(w) > 4]
                
                if significant_words:
                    matches = sum(1 for w in significant_words if w in content_lower)
                    match_ratio = matches / len(significant_words)
                    
                    if match_ratio < 0.3:  # Less than 30% of words found
                        logger.warning(
                            f"Potential hallucination in field '{key}': "
                            f"'{value[:50]}...' has low content match"
                        )
                        return False
        
        return True
