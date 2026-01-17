"""Pydantic models for research API requests and responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ResearchStartRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Research query/topic")
    template_name: Optional[str] = Field(
        None, description="Optional template name (auto-selects if not provided)"
    )
    max_urls: Optional[int] = Field(
        None, ge=1, le=200, description="Maximum number of URLs to crawl"
    )
    generate_report: bool = Field(
        True, description="Whether to generate a synthesized report"
    )


class ResearchStartResponse(BaseModel):
    session_id: str
    status: str
    message: str


class ProgressDetail(BaseModel):
    total_queries: int
    completed_queries: int
    urls_found: int
    urls_to_crawl: int
    urls_crawled: int
    urls_failed: int
    chunks_processed: int
    chunks_for_extraction: int
    facts_extracted: int
    extraction_failures: int


class ResearchStatusResponse(BaseModel):
    session_id: str
    query: str
    template_id: str
    status: str
    progress: ProgressDetail
    start_time: Optional[str]
    end_time: Optional[str]
    error_message: Optional[str]


class FactItem(BaseModel):
    id: str
    fact_data: Dict[str, Any]
    confidence_score: float
    source_url: str
    seed_question: Optional[str] = None


class FactsResponse(BaseModel):
    session_id: str
    facts: List[FactItem]
    total_count: int
    limit: int
    offset: int


class ReportResponse(BaseModel):
    session_id: str
    report_format: str
    content: str
    metadata: Dict[str, Any]


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Template name")
    description: str = Field(..., min_length=1, description="Template description")
    schema_json: Dict[str, Any] = Field(
        ..., description="JSON schema defining the extraction fields"
    )
    system_prompt: Optional[str] = Field(
        None, description="Optional system prompt for extraction"
    )
    seed_questions: Optional[List[str]] = Field(
        None, description="Optional list of seed questions"
    )

    model_config = {"protected_namespaces": ()}


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, min_length=1)
    schema_json: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    seed_questions: Optional[List[str]] = None

    model_config = {"protected_namespaces": ()}


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    schema_json: Dict[str, Any]
    system_prompt: Optional[str]
    seed_questions: Optional[List[str]]
    created_at: str

    model_config = {"protected_namespaces": ()}
