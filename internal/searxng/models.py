"""
Data models for SearXNG web search integration.
"""

from typing import List, Optional, Dict, Any, Literal, Callable
from pydantic import BaseModel, Field


class BangConfig(BaseModel):
    """Configuration for individual bang shortcut"""
    name: str
    description: str
    engine: Optional[str] = None
    category: Optional[str] = None
    shortcut: Optional[str] = None
    query_transform: Optional[Callable[[str], str]] = None


class QueryWithBang(BaseModel):
    """Parsed query with bang and language info"""
    original_query: str
    query: str
    bang: Optional[str] = None
    language: Optional[str] = None


class BangResult(BaseModel):
    """Result of processing a query with bang syntax"""
    original_query: str
    query: str
    language: Optional[str] = None
    category: Optional[str] = None
    engine: Optional[str] = None
    bang: Optional[str] = None


class SearchParams(BaseModel):
    """Internal search parameters for SearXNG client"""
    query: str
    format: str = "json"
    pageno: int = 1
    categories: Optional[str] = None
    language: Optional[str] = None
    time_range: Optional[str] = None
    engine: Optional[str] = None
    per_page: int = 10


class SearchRequest(BaseModel):
    """Unified search request for all categories
    
    Supports searching books, science papers, and social media content.
    
    Usage:
        - Books: category="books" or use bang !ol/!aa
        - Science: category="science" or use bang !arxiv/!gos  
        - Social Media: category="social_media" or use bang !re
    """
    query: str
    category: Optional[Literal["books", "science", "social_media"]] = None
    engine: Optional[str] = Field(None, description="Engine: openlibrary, annas archive, arxiv, google scholar, reddit")
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=100)
    time_range: Optional[Literal["day", "month", "year"]] = None


class SearXNGResult(BaseModel):
    """Individual search result from SearXNG"""
    title: str
    url: str
    content: str
    engine: str
    score: float = 0.0
    category: str = "general"


class SearchResponse(BaseModel):
    """Unified search response for all categories"""
    query: str
    category: Optional[str] = None
    engine: Optional[str] = None
    results: List[SearXNGResult]
    number_of_results: int
    page: int
    per_page: int
    has_next: bool
    has_previous: bool


class CategoryInfo(BaseModel):
    """Information about a search category"""
    name: str
    description: str
    engines: List[str]
    bang_shortcuts: List[str]
    examples: List[str]


class CategoryListResponse(BaseModel):
    """Response with available categories"""
    categories: Dict[str, CategoryInfo]
