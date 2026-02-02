"""
Bang shortcuts registry for SearXNG web search.

Provides:
- Engine-specific bangs (!gh, !so, !arxiv, etc.)
- Category bangs (!images, !map, !science, etc.)
- Language prefix handling (:en, :de, :fr, etc.)
"""

import logging
from typing import Dict, List, Optional, Any, Literal

from .models import BangConfig, QueryWithBang, BangResult
from .exceptions import BangNotFoundError, InvalidBangSyntaxError

logger = logging.getLogger(__name__)


class BangRegistry:
    """
    Registry for managing SearXNG bang shortcuts.
    
    Supports:
    - Engine-specific search: !gh python framework
    - Category search: !images cute cats
    - Language prefixes: :en query or :de query
    """
    
    # Language prefix mappings
    LANGUAGE_PREFIXES = {
        ":en": "en", ":de": "de", ":fr": "fr", ":es": "es",
        ":ja": "ja", ":zh": "zh", ":ru": "ru", ":pt": "pt",
        ":it": "it", ":nl": "nl", ":pl": "pl", ":ko": "ko",
        ":ar": "ar", ":hi": "hi", ":tr": "tr"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the bang registry.
        
        Args:
            config: Optional bang configuration
        """
        self.config = config
        self._bangs: Dict[str, BangConfig] = self._build_default_bangs()
        
        if config:
            self._load_config_bangs()
            
        logger.info(f"Bang registry initialized with {len(self._bangs)} shortcuts")
    
    def _build_default_bangs(self) -> Dict[str, BangConfig]:
        """Build all default bang shortcuts"""
        return {
            # === ENGINE-SPECIFIC BANGS ===
            
            # IT/Files
            "!gh": BangConfig(
                name="GitHub",
                description="Search code repositories on GitHub",
                engine="github",
                query_transform=self._transform_github_query
            ),
            "!so": BangConfig(
                name="Stack Overflow", 
                description="Search programming Q&A on Stack Overflow",
                engine="stackoverflow",
                query_transform=self._transform_site_query
            ),
            "!aw": BangConfig(
                name="ArchWiki",
                description="Search Linux documentation on ArchWiki",
                engine="archwiki",
                query_transform=self._transform_site_query
            ),
            
            # Science/Academic
            "!arxiv": BangConfig(
                name="arXiv",
                description="Search scientific papers on arXiv",
                engine="arxiv",
                query_transform=self._transform_default_query
            ),
            "!scholar": BangConfig(
                name="Google Scholar",
                description="Search academic papers on Google Scholar",
                engine="google scholar",  # Use name (with space), not engine identifier
                query_transform=self._transform_default_query
            ),
            
            # Social Media
            "!lemmy": BangConfig(
                name="Lemmy",
                description="Search fediverse discussions on Lemmy",
                engine="lemmy",
                query_transform=self._transform_default_query
            ),
            "!mastodon": BangConfig(
                name="Mastodon",
                description="Search fediverse posts on Mastodon",
                engine="mastodon",
                query_transform=self._transform_default_query
            ),
            
            # === CATEGORY BANGS ===
            
            "!images": BangConfig(
                name="Images",
                description="Search all image sources",
                category="images",
                query_transform=self._transform_default_query
            ),
            "!map": BangConfig(
                name="Maps",
                description="Search maps and locations",
                category="map",
                query_transform=self._transform_default_query
            ),
            "!videos": BangConfig(
                name="Videos",
                description="Search all video sources",
                category="videos",
                query_transform=self._transform_default_query
            ),
            "!science": BangConfig(
                name="Science",
                description="Search scientific databases",
                category="science",
                query_transform=self._transform_default_query
            ),
            "!it": BangConfig(
                name="IT",
                description="Search IT and programming resources",
                category="it",
                query_transform=self._transform_default_query
            ),
            "!files": BangConfig(
                name="Files",
                description="Search code repositories and file sharing",
                category="files",
                query_transform=self._transform_default_query
            ),
            "!social": BangConfig(
                name="Social Media",
                description="Search social media platforms",
                category="social media",
                query_transform=self._transform_default_query
            ),
            "!news": BangConfig(
                name="News",
                description="Search all news sources",
                category="news",
                query_transform=self._transform_default_query
            ),
            "!general": BangConfig(
                name="General",
                description="Search general web results",
                category="general",
                query_transform=self._transform_default_query
            ),
            
            # === SHORTCUT BANGS ===
            
            "!g": BangConfig(
                name="Google",
                description="Search Google specifically",
                engine="google",
                shortcut="!go"
            ),
            "!b": BangConfig(
                name="Bing",
                description="Search Bing specifically",
                engine="bing",
                shortcut="!bi"
            ),
            "!r": BangConfig(
                name="Reddit",
                description="Search Reddit discussions",
                category="social media",  # Use category for more results
                shortcut="!re",
                query_transform=self._transform_reddit_query
            )
        }
    
    def _transform_github_query(self, query: str) -> str:
        """Transform query for GitHub search"""
        return query
    
    def _transform_site_query(self, query: str) -> str:
        """Transform query for site-specific search"""
        return query
    
    def _transform_reddit_query(self, query: str) -> str:
        """Transform query for Reddit search using Google site:reddit.com"""
        return f"{query} site:reddit.com"
    
    def _transform_default_query(self, query: str) -> str:
        """Default query transformation"""
        return query
    
    def _load_config_bangs(self):
        """Load bang shortcuts from configuration"""
        if not self.config:
            return
            
        for bang_key, bang_data in self.config.items():
            if isinstance(bang_data, dict):
                self._bangs[bang_key] = BangConfig(
                    name=bang_data.get("name", bang_key),
                    description=bang_data.get("description", ""),
                    engine=bang_data.get("engine"),
                    category=bang_data.get("category"),
                    shortcut=bang_data.get("shortcut"),
                    query_transform=bang_data.get("query_transform")
                )
                logger.debug(f"Loaded bang from config: {bang_key}")
    
    def parse_query(self, query: str) -> QueryWithBang:
        """
        Parse a query for bang syntax and language prefix.
        
        Args:
            query: Raw query string (e.g., "!gh python :de" or ":en !images cats")
            
        Returns:
            QueryWithBang with processed query, bang, and language
        """
        # Extract language prefix
        language = None
        processed_query = query
        
        for prefix, lang in self.LANGUAGE_PREFIXES.items():
            if query.startswith(prefix + " "):
                processed_query = query[len(prefix)+1:]
                language = lang
                break
        
        # Extract bang
        bang = None
        parts = processed_query.split(" ")
        
        if parts and parts[0].startswith("!"):
            bang = parts[0]
            processed_query = " ".join(parts[1:])
            
            if bang not in self._bangs:
                raise BangNotFoundError(bang)
        
        return QueryWithBang(
            original_query=query,
            query=processed_query,
            bang=bang,
            language=language
        )
    
    def process_query(self, query: str) -> BangResult:
        """
        Process a query with full bang and language handling.
        
        Args:
            query: Raw query string
            
        Returns:
            BangResult with transformed query and metadata
            
        Raises:
            BangNotFoundError: If bang not found
            InvalidBangSyntaxError: If syntax is invalid
        """
        parsed = self.parse_query(query)
        
        result = BangResult(
            original_query=query,
            query=parsed.query,
            language=parsed.language,
            category=None,
            engine=None,
            bang=parsed.bang
        )
        
        if parsed.bang:
            bang_config = self._bangs[parsed.bang]
            result.engine = bang_config.engine
            result.category = bang_config.category
            
            # Apply query transformation
            if bang_config.query_transform:
                result.query = bang_config.query_transform(parsed.query)
        
        logger.debug(f"Processed query: {query} -> {result.query}")
        return result
    
    def get_bang(self, bang: str) -> Optional[BangConfig]:
        """Get configuration for a specific bang"""
        return self._bangs.get(bang)
    
    def get_all_bangs(self) -> Dict[str, Dict[str, Any]]:
        """Get all available bang shortcuts"""
        result = {}
        for bang, config in self._bangs.items():
            result[bang] = {
                "name": config.name,
                "description": config.description,
                "engine": config.engine,
                "category": config.category,
                "shortcut": config.shortcut
            }
        return result
    
    def list_bangs(self) -> List[str]:
        """Get list of all available bang shortcuts"""
        return list(self._bangs.keys())
    
    def exists(self, bang: str) -> bool:
        """Check if a bang shortcut exists"""
        return bang in self._bangs
    
    def get_bangs_by_category(self, category: str) -> Dict[str, BangConfig]:
        """Get all bangs for a specific category"""
        return {
            bang: config 
            for bang, config in self._bangs.items() 
            if config.category == category
        }
    
    def get_bangs_by_engine(self, engine: str) -> Dict[str, BangConfig]:
        """Get all bangs for a specific engine"""
        return {
            bang: config 
            for bang, config in self._bangs.items() 
            if config.engine == engine
        }
