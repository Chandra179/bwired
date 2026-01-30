"""
Data models for SearXNG web search integration.

This module contains Pydantic models for request/response validation
and data transfer between the SearXNG client and API layer.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class SearXNGSearchRequest(BaseModel):
    """Request model for general web search"""
    query: str
    categories: Optional[str] = Field("general", description="general, news, science, images, videos, files, it, map")
    language: Optional[str] = Field("en", description="Language code")
    time_range: Optional[Literal["day", "week", "month", "year"]] = None
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination")
    per_page: Optional[int] = Field(10, ge=1, le=1000, description="Results per page (max 1000)")
    bang: Optional[str] = Field(None, description="Bang shortcut (e.g., '!news', '!go', '!yhn')")


class BangSyntaxRequest(BaseModel):
    """Request model for bang syntax search"""
    query: str
    bang: str = Field(..., description="Bang shortcut (e.g., '!news', '!go', '!yhn')")
    categories: Optional[str] = Field(None, description="Override category")
    language: Optional[str] = Field("en", description="Language code")
    time_range: Optional[Literal["day", "week", "month", "year"]] = None
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination")
    per_page: Optional[int] = Field(10, ge=1, le=1000, description="Results per page (max 1000)")


class SearXNGResult(BaseModel):
    """Individual search result from SearXNG"""
    title: str
    url: str
    content: str
    engine: str
    score: float
    category: str


class SearXNGSearchResponse(BaseModel):
    """Complete search response from SearXNG"""
    query: str
    number_of_results: int
    results: List[SearXNGResult]
    answers: List[Dict[str, Any]]
    infoboxes: List[Dict[str, Any]]
    suggestions: List[str]
    corrections: List[str]
    page: int
    per_page: int
    has_next: bool
    has_previous: bool


class BangListResponse(BaseModel):
    """Response containing available bang shortcuts"""
    available_bangs: Dict[str, Dict[str, Any]]


# Internal models for client operations
class BangConfig(BaseModel):
    """Configuration for individual bang shortcut"""
    name: str
    description: str
    engines: List[str] = []
    category: Optional[str] = None
    categories: Optional[List[str]] = None


class SearchParams(BaseModel):
    """Internal search parameters for SearXNG client"""
    query: str
    format: str = "json"
    pageno: int = 1
    categories: Optional[str] = None
    language: Optional[str] = None
    time_range: Optional[str] = None