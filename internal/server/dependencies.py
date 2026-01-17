"""FastAPI dependency injection functions for research components."""

from fastapi import HTTPException, Request

from internal.research.template_manager import TemplateManager
from internal.research.research_pipeline import ResearchPipeline
from internal.research.synthesizer import ResearchSynthesizer
from internal.storage.postgres_client import PostgresClient


def get_template_manager(request: Request) -> TemplateManager:
    """Dependency to get template_manager from app state"""
    state = request.app.state.server_state
    if not hasattr(state, "template_manager") or state.template_manager is None:
        raise HTTPException(status_code=503, detail="Template manager not initialized")
    return state.template_manager


def get_research_pipeline(request: Request) -> ResearchPipeline:
    """Dependency to get research_pipeline from app state"""
    state = request.app.state.server_state
    if not hasattr(state, "research_pipeline") or state.research_pipeline is None:
        raise HTTPException(status_code=503, detail="Research pipeline not initialized")
    return state.research_pipeline


def get_synthesizer(request: Request) -> ResearchSynthesizer:
    """Dependency to get synthesizer from app state"""
    state = request.app.state.server_state
    if not hasattr(state, "synthesizer") or state.synthesizer is None:
        raise HTTPException(status_code=503, detail="Synthesizer not initialized")
    return state.synthesizer


def get_postgres_client(request: Request) -> PostgresClient:
    """Dependency to get postgres_client from app state"""
    state = request.app.state.server_state
    if not hasattr(state, "postgres_client") or state.postgres_client is None:
        raise HTTPException(status_code=503, detail="PostgreSQL client not initialized")
    return state.postgres_client
