"""
Bang shortcuts registry for SearXNG web search.

Provides bang shortcuts for 3 categories:
- Books: !ol, !aa
- Science: !arxiv, !gos
- Social Media: !re
- Category shortcuts: !books, !science, !social
"""

import logging
from typing import Dict, List, Optional, Any

from .models import BangConfig, QueryWithBang, BangResult
from .exceptions import BangNotFoundError

logger = logging.getLogger(__name__)


class BangRegistry:
    """
    Registry for managing SearXNG bang shortcuts.
    Supports 5 engine bangs and 3 category bangs.
    """
    
    def __init__(self):
        """Initialize the bang registry with 8 essential bangs."""
        self._bangs: Dict[str, BangConfig] = self._build_bangs()
        logger.info(f"Bang registry initialized with {len(self._bangs)} shortcuts")
    
    def _build_bangs(self) -> Dict[str, BangConfig]:
        """Build all bang shortcuts for books, science, and social media."""
        return {
            # === BOOKS CATEGORY ===
            "!ol": BangConfig(
                name="OpenLibrary",
                description="Search books on OpenLibrary",
                engine="openlibrary",
                category="books"
            ),
            "!aa": BangConfig(
                name="Anna's Archive",
                description="Search books on Anna's Archive",
                engine="annas archive",
                category="books"
            ),
            
            # === SCIENCE CATEGORY ===
            "!arxiv": BangConfig(
                name="arXiv",
                description="Search scientific papers on arXiv",
                engine="arxiv",
                category="science"
            ),
            "!gos": BangConfig(
                name="Google Scholar",
                description="Search academic papers on Google Scholar",
                engine="google scholar",
                category="science"
            ),
            
            # === SOCIAL MEDIA CATEGORY ===
            "!re": BangConfig(
                name="Reddit",
                description="Search Reddit discussions",
                engine="reddit",
                category="social_media"
            ),
            
            # === CATEGORY BANGS ===
            "!books": BangConfig(
                name="Books",
                description="Search all book sources (OpenLibrary, Anna's Archive)",
                category="books"
            ),
            "!science": BangConfig(
                name="Science",
                description="Search all scientific databases (arXiv, Google Scholar)",
                category="science"
            ),
            "!social": BangConfig(
                name="Social Media",
                description="Search social media platforms (Reddit)",
                category="social_media"
            ),
        }
    
    def parse_query(self, query: str) -> QueryWithBang:
        """
        Parse a query for bang syntax.
        
        Args:
            query: Raw query string (e.g., "!ol python programming")
            
        Returns:
            QueryWithBang with processed query and bang
        """
        bang = None
        processed_query = query
        
        parts = query.split(" ")
        if parts and parts[0].startswith("!"):
            bang = parts[0]
            processed_query = " ".join(parts[1:])
            
            if bang not in self._bangs:
                raise BangNotFoundError(bang)
        
        return QueryWithBang(
            original_query=query,
            query=processed_query,
            bang=bang,
            language=None
        )
    
    def process_query(self, query: str) -> BangResult:
        """
        Process a query with full bang handling.
        
        Args:
            query: Raw query string
            
        Returns:
            BangResult with transformed query and metadata
        """
        parsed = self.parse_query(query)
        
        result = BangResult(
            original_query=query,
            query=parsed.query,
            language=None,
            category=None,
            engine=None,
            bang=parsed.bang
        )
        
        if parsed.bang:
            bang_config = self._bangs[parsed.bang]
            result.engine = bang_config.engine
            result.category = bang_config.category
        
        logger.debug(f"Processed query: {query} -> {result.query} (engine: {result.engine}, category: {result.category})")
        return result
    
    def get_bang(self, bang: str) -> Optional[BangConfig]:
        """Get configuration for a specific bang."""
        return self._bangs.get(bang)
    
    def get_all_bangs(self) -> Dict[str, Dict[str, Any]]:
        """Get all available bang shortcuts."""
        result = {}
        for bang, config in self._bangs.items():
            result[bang] = {
                "name": config.name,
                "description": config.description,
                "engine": config.engine,
                "category": config.category
            }
        return result
    
    def list_bangs(self) -> List[str]:
        """Get list of all available bang shortcuts."""
        return list(self._bangs.keys())
    
    def exists(self, bang: str) -> bool:
        """Check if a bang shortcut exists."""
        return bang in self._bangs
    
    def get_bangs_by_category(self, category: str) -> Dict[str, BangConfig]:
        """Get all bangs for a specific category."""
        return {
            bang: config 
            for bang, config in self._bangs.items() 
            if config.category == category
        }
    
    def get_bangs_by_engine(self, engine: str) -> Dict[str, BangConfig]:
        """Get all bangs for a specific engine."""
        return {
            bang: config 
            for bang, config in self._bangs.items() 
            if config.engine == engine
        }
