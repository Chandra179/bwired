from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseProcessor(ABC):
    """Abstract base class for processing search results"""
    
    @abstractmethod
    def process(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process search results
        
        Args:
            results: List of search results with scores, content, and metadata
            
        Returns:
            Dictionary containing processed results
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if processor is enabled
        
        Returns:
            True if processor should be applied, False otherwise
        """
        pass