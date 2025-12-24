"""Core utilities for chunking - no longer includes SectionAnalyzer"""
from .overlap_handler import OverlapHandler
from .metadata import ChunkMetadata

__all__ = ['OverlapHandler', 'ChunkMetadata']