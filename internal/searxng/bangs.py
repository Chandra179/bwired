"""
Bang shortcuts registry for SearXNG web search.

This module provides a configurable registry for bang shortcuts
that can be used to direct searches to specific search engines
or categories.
"""

import logging
from typing import Dict, List, Optional, Any

from .models import BangConfig
from .exceptions import SearXNGBangNotFoundError

logger = logging.getLogger(__name__)


class BangRegistry:
    """
    Registry for managing SearXNG bang shortcuts.
    
    Provides configurable bang shortcuts that can be loaded from
    the application configuration or use defaults.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the bang registry.
        
        Args:
            config: Optional bang configuration from config.yaml
        """
        self.config = config
        self._bangs: Dict[str, BangConfig] = {}
        self._load_default_bangs()
        if config:
            self._load_config_bangs()
        logger.info(f"Bang registry initialized with {len(self._bangs)} shortcuts")
    
    def _load_default_bangs(self):
        """Load default bang shortcuts"""
        default_bangs = {
            # Categories
            "!news": BangConfig(
                name="All News Engines",
                description="Search all enabled news sources",
                engines=["Google News", "Bing News", "Yahoo News", "DuckDuckGo News", "Qwant News", "Reddit", "Twitter"]
            ),
            "!images": BangConfig(
                name="All Images",
                description="Search all image sources",
                engines=["Google Images", "Bing Images", "DuckDuckGo Images", "Qwant Images"]
            ),
            "!videos": BangConfig(
                name="All Videos",
                description="Search all video sources",
                engines=["YouTube", "Google Videos", "Bing Videos", "DuckDuckGo Videos"]
            ),
            "!map": BangConfig(
                name="Maps",
                description="Search maps and locations",
                engines=["OpenStreetMap"]
            ),
            
            # News Engines
            "!yhn": BangConfig(
                name="Yahoo News",
                description="Search Yahoo News specifically",
                category="news"
            ),
            "!ddn": BangConfig(
                name="DuckDuckGo News",
                description="Search DuckDuckGo News specifically",
                category="news"
            ),
            "!qwn": BangConfig(
                name="Qwant News",
                description="Search Qwant News specifically",
                category="news"
            ),
            
            # General Search Engines
            "!go": BangConfig(
                name="Google",
                description="Search Google specifically",
                categories=["general", "news"]
            ),
            "!bi": BangConfig(
                name="Bing",
                description="Search Bing specifically",
                categories=["general", "news"]
            ),
            "!br": BangConfig(
                name="Brave",
                description="Search Brave specifically",
                categories=["general", "news"]
            ),
            "!re": BangConfig(
                name="Reddit",
                description="Search Reddit (custom Google search)",
                categories=["news", "general"]
            )
        }
        self._bangs.update(default_bangs)
    
    def _load_config_bangs(self):
        """Load bang shortcuts from configuration"""
        if not self.config:
            return
            
        for bang_key, bang_data in self.config.items():
            if isinstance(bang_data, dict):
                self._bangs[bang_key] = BangConfig(
                    name=bang_data.get("name", bang_key),
                    description=bang_data.get("description", ""),
                    engines=bang_data.get("engines", []),
                    category=bang_data.get("category"),
                    categories=bang_data.get("categories")
                )
                logger.debug(f"Loaded bang from config: {bang_key}")
    
    def get_bang(self, bang: str) -> Optional[BangConfig]:
        """
        Get configuration for a specific bang shortcut.
        
        Args:
            bang: Bang shortcut (e.g., '!news', '!go')
            
        Returns:
            BangConfig if found, None otherwise
        """
        return self._bangs.get(bang)
    
    def process_query_with_bang(self, query: str, bang: str) -> str:
        """
        Apply bang syntax to query with special handling.
        
        Args:
            query: Original search query
            bang: Bang shortcut to apply
            
        Returns:
            Modified query with bang applied
        """
        bang_config = self.get_bang(bang)
        if not bang_config:
            raise SearXNGBangNotFoundError(bang)
        
        # Special handling for reddit bang to enforce site-specific search
        if bang == "!re":
            processed_query = f"site:reddit.com {query}"
            logger.info(f"Reddit bang detected - transformed query to: {processed_query}")
            return processed_query
        
        # Default bang processing
        processed_query = f"{bang} {query}"
        logger.debug(f"Applied bang '{bang}' to query: {processed_query}")
        return processed_query
    
    def get_all_bangs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available bang shortcuts as a dictionary.
        
        Returns:
            Dictionary with bang as key and config data as value
        """
        result = {}
        for bang, config in self._bangs.items():
            result[bang] = {
                "name": config.name,
                "description": config.description,
                "engines": config.engines,
                "category": config.category,
                "categories": config.categories
            }
        return result
    
    def list_bangs(self) -> List[str]:
        """
        Get list of all available bang shortcuts.
        
        Returns:
            List of bang strings
        """
        return list(self._bangs.keys())
    
    def exists(self, bang: str) -> bool:
        """
        Check if a bang shortcut exists.
        
        Args:
            bang: Bang shortcut to check
            
        Returns:
            True if bang exists, False otherwise
        """
        return bang in self._bangs