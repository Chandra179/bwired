"""
Embedding components for the markdown_chunker package.

This package provides three independent components for embedding and reranking:
- DenseEmbedder: Generate dense semantic embeddings using SentenceTransformer
- SparseEmbedder: Generate sparse lexical embeddings using SPLADE
- Reranker: Rerank search results using CrossEncoder models
"""

from .dense_embedder import DenseEmbedder
from .sparse_embedder import SparseEmbedder
from .reranker import Reranker

__all__ = [
    'DenseEmbedder',
    'SparseEmbedder',
    'Reranker',
]

__version__ = '2.0.0'  # Version after refactoring