"""
Agents module - Agentic AI layer for document operations
"""
from internal.agents.factory import create_document_agent
from internal.agents.search_agent import search_documents

__all__ = [
    'create_document_agent',
    'search_documents',
]