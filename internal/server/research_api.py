"""Research session management endpoints."""
import logging
import asyncio

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional

from internal.research.research_pipeline import ResearchPipeline
from internal.research.synthesizer import ResearchSynthesizer
from internal.storage.postgres_client import PostgresClient
from internal.server.dependencies import (
    get_research_pipeline,
    get_synthesizer,
    get_postgres_client,
)
from internal.server.schemas.research import (
    ResearchStartRequest,
    ResearchStartResponse,
    ProgressDetail,
    ResearchStatusResponse,
    FactItem,
    FactsResponse,
    ReportResponse,
)
from internal.server.errors import (
    handle_not_found,
    handle_validation_error,
    log_and_raise_internal_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


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
    """Start a new research session."""
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
        handle_validation_error(str(e))
    except Exception as e:
        log_and_raise_internal_error("start research", e)


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
    """Get the current status of a research session."""
    try:
        session_info = postgres_client.get_session_info(session_id)

        if not session_info:
            handle_not_found("Research session", session_id)

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
        log_and_raise_internal_error("retrieve session status", e)


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
    """Get extracted facts from a research session."""
    try:
        session_info = postgres_client.get_session_info(session_id)

        if not session_info:
            handle_not_found("Research session", session_id)

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
        log_and_raise_internal_error("retrieve facts", e)


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
    """Get the synthesized report for a research session."""
    try:
        session_info = postgres_client.get_session_info(session_id)

        if not session_info:
            handle_not_found("Research session", session_id)

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

        report = await synthesizer.synthesize_report(session_id, force_regenerate=False)
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
        log_and_raise_internal_error("retrieve report", e)
