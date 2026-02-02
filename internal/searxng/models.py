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


class SearXNGSearchRequest(BaseModel):
    """Request model for web search"""
    query: str
    category: Optional[str] = Field(None, description="Search category")
    language: Optional[str] = Field("en", description="Language code")
    time_range: Optional[Literal["day", "month", "year"]] = None


class SpecializedSearchRequest(BaseModel):
    """Request for specialized category search"""
    query: str
    category: Literal[
        "general", "it", "science", "social", "files", 
        "images", "map", "videos", "news"
    ] = "general"
    language: Optional[str] = "en"
    time_range: Optional[Literal["day", "month", "year"]] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=100)
    bang: Optional[str] = None


class SearXNGResult(BaseModel):
    """Individual search result from SearXNG"""
    title: str
    url: str
    content: str
    engine: str
    score: float = 0.0
    category: str = "general"


class SearXNGSearchResponse(BaseModel):
    """Complete search response from SearXNG"""
    query: str
    number_of_results: int
    results: List[SearXNGResult]
    answers: List[Dict[str, Any]] = []
    infoboxes: List[Dict[str, Any]] = []
    suggestions: List[str] = []
    corrections: List[str] = []
    page: int
    per_page: int
    has_next: bool
    has_previous: bool


class SpecializedSearchResponse(BaseModel):
    """Response for specialized search"""
    query: str
    category: str
    language: Optional[str]
    results: List[SearXNGResult]
    number_of_results: int
    engine: Optional[str] = None
    page: int
    per_page: int
    has_next: bool
    has_previous: bool


class CategoryInfo(BaseModel):
    """Information about a search category"""
    name: str
    description: str
    bang_shortcuts: List[str]


class EngineInfo(BaseModel):
    """Information about a search engine"""
    name: str
    categories: List[str]
    shortcut: Optional[str]


class CategoryListResponse(BaseModel):
    """Response with available categories"""
    categories: Dict[str, CategoryInfo]


class EngineListResponse(BaseModel):
    """Response with available engines"""
    engines: List[EngineInfo]


class BangListResponse(BaseModel):
    """Response containing available bang shortcuts"""
    bangs: Dict[str, Dict[str, Any]]


class BangSyntaxRequest(BaseModel):
    """Request model for bang syntax search"""
    query: str
    bang: str = Field(..., description="Bang shortcut")
    category: Optional[str] = None
    language: Optional[str] = Field("en", description="Language code")
    time_range: Optional[Literal["day", "month", "year"]] = None
    page: Optional[int] = Field(1, ge=1)
    per_page: Optional[int] = Field(10, ge=1, le=1000)
