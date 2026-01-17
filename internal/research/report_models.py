from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ReportSection(BaseModel):
    title: str
    content: str
    seed_question: Optional[str] = None
    fact_count: int
    citations: List[str] = Field(default_factory=list)


class ExecutiveSummary(BaseModel):
    overview: str
    key_findings_count: int
    primary_conclusions: List[str]
    confidence_level: str


class DetailedFindings(BaseModel):
    sections: List[ReportSection]
    thematic_groupings: Dict[str, Any] = Field(default_factory=dict)
    total_facts_used: int


class KeyInsight(BaseModel):
    insight: str
    supporting_facts: List[str]
    confidence: float


class SynthesizedReport(BaseModel):
    session_id: str
    executive_summary: ExecutiveSummary
    detailed_findings: DetailedFindings
    key_insights: List[KeyInsight]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
