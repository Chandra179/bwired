from fastapi import APIRouter, HTTPException, status, Depends, Request, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from internal.research.template_manager import TemplateManager
from internal.research.research_pipeline import ResearchPipeline
from internal.research.synthesizer import ResearchSynthesizer
from internal.research.models import validate_template_schema
from internal.storage.postgres_client import PostgresClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


def get_template_manager(request: Request) -> TemplateManager:
    """Dependency to get template_manager from app state"""
    state = request.app.state.server_state
    if not hasattr(state, 'template_manager') or state.template_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Template manager not initialized"
        )
    return state.template_manager


def get_research_pipeline(request: Request) -> ResearchPipeline:
    """Dependency to get research_pipeline from app state"""
    state = request.app.state.server_state
    if not hasattr(state, 'research_pipeline') or state.research_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Research pipeline not initialized"
        )
    return state.research_pipeline


def get_synthesizer(request: Request) -> ResearchSynthesizer:
    """Dependency to get synthesizer from app state"""
    state = request.app.state.server_state
    if not hasattr(state, 'synthesizer') or state.synthesizer is None:
        raise HTTPException(
            status_code=503,
            detail="Synthesizer not initialized"
        )
    return state.synthesizer


def get_postgres_client(request: Request) -> PostgresClient:
    """Dependency to get postgres_client from app state"""
    state = request.app.state.server_state
    if not hasattr(state, 'postgres_client') or state.postgres_client is None:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL client not initialized"
        )
    return state.postgres_client


class ResearchStartRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Research query/topic")
    template_name: Optional[str] = Field(None, description="Optional template name (auto-selects if not provided)")
    max_urls: Optional[int] = Field(None, ge=1, le=200, description="Maximum number of URLs to crawl")
    generate_report: bool = Field(True, description="Whether to generate a synthesized report")


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
    schema_json: Dict[str, Any] = Field(..., description="JSON schema defining the extraction fields")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt for extraction")
    seed_questions: Optional[List[str]] = Field(None, description="Optional list of seed questions")

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


@router.post(
    "/start",
    response_model=ResearchStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a new research session",
    description="Initiates a deep research session that runs in the background. Returns a session ID for polling progress."
)
async def start_research(
    request_data: ResearchStartRequest,
    pipeline: ResearchPipeline = Depends(get_research_pipeline)
) -> ResearchStartResponse:
    """
    Start a new research session.

    The research runs asynchronously in the background. Use the returned session_id
    to poll the /status endpoint for progress updates.
    """
    try:
        logger.info(f"Starting research for query: {request_data.query[:100]}...")

        session_id = await pipeline.run_async(
            query=request_data.query,
            template_name=request_data.template_name,
            max_urls=request_data.max_urls
        )

        logger.info(f"Research session started: {session_id}")

        return ResearchStartResponse(
            session_id=session_id,
            status="started",
            message="Research initiated. Poll /status endpoint for progress."
        )

    except ValueError as e:
        logger.error(f"Validation error starting research: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error starting research: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start research: {str(e)}"
        )


@router.get(
    "/{session_id}/status",
    response_model=ResearchStatusResponse,
    summary="Get research session status",
    description="Retrieves the current status and progress of a research session."
)
async def get_research_status(
    session_id: str,
    postgres_client: PostgresClient = Depends(get_postgres_client)
) -> ResearchStatusResponse:
    """
    Get the current status of a research session.

    Returns detailed progress metrics including URLs crawled, chunks processed,
    and facts extracted.
    """
    try:
        session_info = postgres_client.get_session_info(session_id)

        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session '{session_id}' not found"
            )

        progress = session_info.get('progress', {})

        return ResearchStatusResponse(
            session_id=session_info['id'],
            query=session_info['query'],
            template_id=str(session_info['template_id']),
            status=session_info['status'],
            progress=ProgressDetail(**progress),
            start_time=session_info.get('start_time'),
            end_time=session_info.get('end_time'),
            error_message=session_info.get('error_message')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session status: {str(e)}"
        )


@router.get(
    "/{session_id}/facts",
    response_model=FactsResponse,
    summary="Get extracted facts",
    description="Retrieves all extracted facts from a research session with pagination support."
)
async def get_session_facts(
    session_id: str,
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    limit: int = Query(50, ge=1, le=500, description="Number of facts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    postgres_client: PostgresClient = Depends(get_postgres_client)
) -> FactsResponse:
    """
    Get extracted facts from a research session.

    Supports pagination via `limit` and `offset` parameters.
    Can filter facts by minimum confidence score.
    """
    try:
        session_info = postgres_client.get_session_info(session_id)

        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session '{session_id}' not found"
            )

        threshold = min_confidence if min_confidence is not None else 0.7

        all_facts = postgres_client.get_facts_by_session(
            session_id=session_id,
            min_confidence=threshold
        )

        total_count = len(all_facts)
        paginated_facts = all_facts[offset:offset + limit]

        fact_items = [
            FactItem(
                id=fact['id'],
                fact_data=fact['fact_data'],
                confidence_score=fact['confidence_score'],
                source_url=fact['source_url'],
                seed_question=fact.get('seed_question')
            )
            for fact in paginated_facts
        ]

        return FactsResponse(
            session_id=session_id,
            facts=fact_items,
            total_count=total_count,
            limit=limit,
            offset=offset
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving facts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve facts: {str(e)}"
        )


@router.get(
    "/{session_id}/report",
    response_model=ReportResponse,
    summary="Get synthesized research report",
    description="Retrieves the synthesized report for a completed research session. Returns 404 if the report does not exist."
)
async def get_session_report(
    session_id: str,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    synthesizer: ResearchSynthesizer = Depends(get_synthesizer)
) -> ReportResponse:
    """
    Get the synthesized report for a research session.

    The report is generated during the research process if `generate_report` was enabled.
    Returns the report in markdown format.
    """
    import asyncio

    try:
        session_info = postgres_client.get_session_info(session_id)

        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session '{session_id}' not found"
            )

        if session_info['status'] not in ['completed', 'synthesizing']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Report not available. Session status: {session_info['status']}"
            )

        if not postgres_client.has_report(session_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found. Ensure research completed with report generation enabled."
            )

        report = asyncio.run(synthesizer.synthesize_report(session_id, force_regenerate=False))
        report_content = synthesizer.generate_markdown_report(session_id, report)

        metadata = {
            "total_facts": report.metadata.get('total_facts', 0),
            "unique_sources": report.metadata.get('unique_sources', 0),
            "avg_confidence": report.metadata.get('avg_confidence', 0.0),
            "generated_at": report.generated_at.isoformat() if report.generated_at else None
        }

        return ReportResponse(
            session_id=session_id,
            report_format="markdown",
            content=report_content,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}"
        )


