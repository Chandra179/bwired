"""Processing module for post-processing search results"""

from .base_processor import BaseProcessor
from .context_compressor import ContextCompressor

__all__ = [
    'BaseProcessor',
    'ContextCompressor',
]