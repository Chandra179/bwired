"""
Markdown Chunking and Embedding System

A modular system for parsing markdown documents, chunking them intelligently
based on token limits, generating embeddings, and storing in Qdrant vector database.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .config import EmbeddingConfig, QdrantConfig
from .parser import MarkdownParser, MarkdownElement, ElementType
from .tokenizer_utils import TokenCounter
from .chunker import MarkdownChunker, Chunk
from .embedder import EmbeddingGenerator
from .metadata import ChunkMetadata
from .storage import QdrantStorage

__all__ = [
    'EmbeddingConfig',
    'QdrantConfig',
    'MarkdownParser',
    'MarkdownElement',
    'ElementType',
    'TokenCounter',
    'MarkdownChunker',
    'Chunk',
    'EmbeddingGenerator',
    'ChunkMetadata',
    'QdrantStorage',
]