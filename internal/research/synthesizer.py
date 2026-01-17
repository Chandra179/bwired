import logging
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader

from internal.storage.postgres_client import PostgresClient
from internal.llm.base import LLMClient, ExtractionResult
from internal.research.report_models import (
    SynthesizedReport, ReportSection, ExecutiveSummary,
    DetailedFindings, KeyInsight
)
from internal.config import SynthesisConfig

logger = logging.getLogger(__name__)


@dataclass
class AggregatedFacts:
    session_id: str
    total_facts: int
    facts_by_question: Dict[str, List[Dict]]
    all_facts: List[Dict]
    unique_sources: Set[str]
    domain_counts: Dict[str, int]
    avg_confidence: float


class ResearchSynthesizer:
    def __init__(
        self,
        postgres_client: PostgresClient,
        llm_client: LLMClient,
        config: SynthesisConfig
    ):
        self.postgres = postgres_client
        self.llm = llm_client
        self.config = config
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=False
        )
        logger.info(f"ResearchSynthesizer initialized with {config.report_format} format")
    
    async def aggregate_facts(
        self,
        session_id: str,
        min_confidence: Optional[float] = None
    ) -> AggregatedFacts:
        min_conf = min_confidence or self.config.min_confidence
        
        logger.info(f"Aggregating facts for session {session_id} (min_conf: {min_conf})")
        
        facts = self.postgres.get_facts_by_session(session_id, min_conf)
        
        if not facts:
            logger.warning(f"No facts found for session {session_id}")
            return self._empty_aggregation(session_id)
        
        facts_by_question = self._group_facts_by_question(facts)
        unique_sources = {f['source_url'] for f in facts}
        domain_counts = self._count_domains(facts)
        avg_confidence = sum(f['confidence_score'] for f in facts) / len(facts)
        
        return AggregatedFacts(
            session_id=session_id,
            total_facts=len(facts),
            facts_by_question=facts_by_question,
            all_facts=facts,
            unique_sources=unique_sources,
            domain_counts=domain_counts,
            avg_confidence=avg_confidence
        )
    
    def _group_facts_by_question(self, facts: List[Dict]) -> Dict[str, List[Dict]]:
        grouped: Dict[str, List[Dict]] = {}
        
        for fact in facts:
            question = fact.get('seed_question', 'general')
            if question not in grouped:
                grouped[question] = []
            grouped[question].append(fact)
        
        return grouped
    
    def _count_domains(self, facts: List[Dict]) -> Dict[str, int]:
        domain_counts: Dict[str, int] = {}
        
        for fact in facts:
            url = fact['source_url']
            domain = self._extract_domain(url)
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        return domain_counts
    
    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc
    
    def _empty_aggregation(self, session_id: str) -> AggregatedFacts:
        return AggregatedFacts(
            session_id=session_id,
            total_facts=0,
            facts_by_question={},
            all_facts=[],
            unique_sources=set(),
            domain_counts={},
            avg_confidence=0.0
        )
    
    async def synthesize_report(
        self,
        session_id: str,
        force_regenerate: bool = False
    ) -> SynthesizedReport:
        if not force_regenerate and self.postgres.has_report(session_id):
            logger.info(f"Report exists for session {session_id}, loading from database")
            return await self._load_existing_report(session_id)
        
        logger.info(f"Synthesizing new report for session {session_id}")
        
        aggregated = await self.aggregate_facts(session_id)
        
        if aggregated.total_facts == 0:
            logger.warning(f"No facts to synthesize for session {session_id}")
            raise ValueError("No facts available for synthesis")
        
        executive_summary = await self._synthesize_executive_summary(aggregated)
        detailed_findings = await self._synthesize_detailed_findings(aggregated)
        key_insights = await self._extract_key_insights(aggregated)
        
        report = SynthesizedReport(
            session_id=session_id,
            executive_summary=executive_summary,
            detailed_findings=detailed_findings,
            key_insights=key_insights,
            metadata={
                'total_facts': aggregated.total_facts,
                'unique_sources': len(aggregated.unique_sources),
                'avg_confidence': aggregated.avg_confidence,
                'domain_counts': aggregated.domain_counts
            }
        )
        
        self._store_report_sections(session_id, report)
        
        logger.info(f"Report synthesized and stored for session {session_id}")
        return report
    
    async def _load_existing_report(self, session_id: str) -> SynthesizedReport:
        data = self.postgres.get_report_sections(session_id)
        
        if not data:
            raise ValueError(f"No report found for session {session_id}")
        
        sections = [
            ReportSection(**s) for s in data['sections']
        ]
        
        return SynthesizedReport(
            session_id=session_id,
            executive_summary=ExecutiveSummary(
                overview=data['executive_summary_overview'],
                key_findings_count=data.get('total_facts_analyzed', 0),
                primary_conclusions=data['executive_summary_conclusions'],
                confidence_level=data['executive_summary_confidence']
            ),
            detailed_findings=DetailedFindings(
                sections=sections,
                total_facts_used=data['total_facts_analyzed']
            ),
            key_insights=[
                KeyInsight(**i) for i in data['key_insights']
            ],
            metadata={
                'total_facts': data['total_facts_analyzed'],
                'unique_sources': data['unique_sources_count'],
                'avg_confidence': data['avg_confidence'],
                'domain_counts': data['domain_counts']
            },
            generated_at=data['generated_at']
        )
    
    def _store_report_sections(self, session_id: str, report: SynthesizedReport) -> None:
        self.postgres.store_report_sections(
            session_id=session_id,
            executive_summary_overview=report.executive_summary.overview,
            executive_summary_conclusions=report.executive_summary.primary_conclusions,
            executive_summary_confidence=report.executive_summary.confidence_level,
            sections=[s.model_dump() for s in report.detailed_findings.sections],
            sections_count=len(report.detailed_findings.sections),
            key_insights=[i.model_dump() for i in report.key_insights],
            insights_count=len(report.key_insights),
            total_facts_analyzed=report.metadata.get('total_facts', 0),
            unique_sources_count=report.metadata.get('unique_sources', 0),
            avg_confidence=report.metadata.get('avg_confidence', 0.0),
            domain_counts=report.metadata.get('domain_counts', {})
        )
    
    async def _synthesize_executive_summary(
        self,
        aggregated: AggregatedFacts
    ) -> ExecutiveSummary:
        class ExecSummary(BaseModel):
            overview: str
            primary_conclusions: List[str]
            confidence_level: str
        
        facts_summary = self._format_facts_for_summary(aggregated.all_facts)
        
        system_prompt = """You are a research analyst synthesizing findings from multiple sources.

Your task:
1. Write a concise overview (3-4 sentences) of research findings
2. Extract 5-7 primary conclusions
3. Assess overall confidence level based on fact confidence scores

Confidence levels:
- "high" if avg confidence > 0.85 and diverse sources
- "medium" if avg confidence > 0.70
- "low" if avg confidence <= 0.70"""

        content = f"""Research Session: {aggregated.session_id}

Total Facts: {aggregated.total_facts}
Unique Sources: {len(aggregated.unique_sources)}
Average Confidence: {aggregated.avg_confidence:.2f}

Extracted Facts Summary:
{facts_summary}"""

        result = await self.llm.extract_structured(
            content=content,
            output_model=ExecSummary,
            system_prompt=system_prompt,
            max_retries=2
        )
        
        if not result.success:
            logger.error(f"Failed to synthesize executive summary: {result.error}")
            return self._fallback_executive_summary(aggregated)
        
        return ExecutiveSummary(
            overview=result.data.overview,
            key_findings_count=aggregated.total_facts,
            primary_conclusions=result.data.primary_conclusions,
            confidence_level=result.data.confidence_level
        )
    
    def _format_facts_for_summary(self, facts: List[Dict]) -> str:
        sorted_facts = sorted(facts, key=lambda f: f['confidence_score'], reverse=True)
        top_facts = sorted_facts[:10]
        
        lines = []
        for i, fact in enumerate(top_facts, 1):
            fact_data = fact['fact_data']
            lines.append(f"{i}. {self._format_fact_data(fact_data)}")
        
        return "\n".join(lines)
    
    def _format_fact_data(self, fact_data: Dict) -> str:
        parts = []
        for key, value in fact_data.items():
            if isinstance(value, (list, dict)):
                parts.append(f"{key}: {str(value)[:100]}...")
            else:
                parts.append(f"{key}: {value}")
        return "; ".join(parts)
    
    def _fallback_executive_summary(
        self,
        aggregated: AggregatedFacts
    ) -> ExecutiveSummary:
        confidence_map = {
            (0.85, 1.0): "high",
            (0.70, 0.85): "medium",
            (0.0, 0.70): "low"
        }
        
        for (low, high), level in confidence_map.items():
            if low <= aggregated.avg_confidence < high:
                confidence = level
                break
        else:
            confidence = "medium"
        
        return ExecutiveSummary(
            overview=f"Research completed with {aggregated.total_facts} facts from {len(aggregated.unique_sources)} sources.",
            key_findings_count=aggregated.total_facts,
            primary_conclusions=[
                f"Analyzed {aggregated.total_facts} facts across multiple sources",
                f"Average confidence score: {aggregated.avg_confidence:.2f}",
                "See detailed findings for specific conclusions"
            ],
            confidence_level=confidence
        )
    
    async def _synthesize_detailed_findings(
        self,
        aggregated: AggregatedFacts
    ) -> DetailedFindings:
        sections: List[ReportSection] = []
        
        for question, facts in aggregated.facts_by_question.items():
            section_facts = sorted(
                facts,
                key=lambda f: f['confidence_score'],
                reverse=True
            )[:self.config.max_facts_per_section]
            
            section = await self._synthesize_section(
                question=question,
                facts=section_facts
            )
            sections.append(section)
        
        return DetailedFindings(
            sections=sections,
            total_facts_used=aggregated.total_facts
        )
    
    async def _synthesize_section(
        self,
        question: str,
        facts: List[Dict]
    ) -> ReportSection:
        class SectionContent(BaseModel):
            title: str
            content: str
            key_points: List[str]
        
        facts_text = self._format_facts_with_citations(facts)
        
        system_prompt = """You are synthesizing research findings into a coherent section.

Your task:
1. Write a descriptive title for this section (based on research question)
2. Create a comprehensive narrative (3-5 paragraphs) that:
   - Synthesizes facts into a coherent story
   - Maintains factual accuracy
   - Uses citations in [url] format when referencing specific sources
   - Identifies patterns, trends, and relationships
3. Extract 5-7 key points

 Citation format: Always include [source_url] when referencing specific facts.

 Example:
 "The study found that X [https://example.com/study1], while other research suggested Y [https://example.com/study2]."""

        content = f"""Research Question: {question}

 Number of Facts: {len(facts)}

 Extracted Facts:
{facts_text}"""

        result = await self.llm.extract_structured(
            content=content,
            output_model=SectionContent,
            system_prompt=system_prompt,
            max_retries=2
        )
        
        if not result.success:
            logger.error(f"Failed to synthesize section for {question}: {result.error}")
            return self._fallback_section(question, facts)
        
        citations = self._extract_citations(result.data.content)
        
        return ReportSection(
            title=result.data.title,
            content=result.data.content,
            seed_question=question,
            fact_count=len(facts),
            citations=citations
        )
    
    def _format_facts_with_citations(self, facts: List[Dict]) -> str:
        lines = []
        for i, fact in enumerate(facts, 1):
            url = fact['source_url']
            data_str = self._format_fact_data(fact['fact_data'])
            lines.append(f"{i}. {data_str} [{url}]")
            lines.append(f"   Confidence: {fact['confidence_score']:.2f}")
        
        return "\n".join(lines)
    
    def _extract_citations(self, content: str) -> List[str]:
        import re
        pattern = r'\[(https?://[^\]]+)\]'
        matches = re.findall(pattern, content)
        return list(set(matches))
    
    def _fallback_section(
        self,
        question: str,
        facts: List[Dict]
    ) -> ReportSection:
        facts_text = "\n".join([
            f"- {self._format_fact_data(f['fact_data'])} [{f['source_url']}]"
            for f in facts[:5]
        ])
        
        content = f"""Analysis of {question}

Key findings based on {len(facts)} extracted facts:

{facts_text}

Note: This section was auto-generated. Full synthesis pending LLM processing."""
        
        return ReportSection(
            title=f"Findings: {question}",
            content=content,
            seed_question=question,
            fact_count=len(facts),
            citations=[f['source_url'] for f in facts]
        )
    
    async def _extract_key_insights(
        self,
        aggregated: AggregatedFacts
    ) -> List[KeyInsight]:
        class InsightsList(BaseModel):
            insights: List[Dict[str, Any]]
        
        all_facts = aggregated.all_facts
        if len(all_facts) > 30:
            top_facts = sorted(all_facts, key=lambda f: f['confidence_score'], reverse=True)[:10]
            import random
            random.seed(42)
            remaining = [f for f in all_facts if f not in top_facts]
            sampled_facts = top_facts + random.sample(remaining, 20)
        else:
            sampled_facts = all_facts
        
        facts_text = self._format_facts_with_citations(sampled_facts)
        
        system_prompt = """You are identifying key insights that emerge across all research findings.

Your task:
Extract 5-7 key insights that:
1. Cross multiple research questions (not specific to one)
2. Represent significant patterns, contradictions, or discoveries
3. Are well-supported by facts (high confidence)
4. Have practical or theoretical importance

For each insight, provide:
- insight: The insight statement
- supporting_facts: Brief descriptions of 3-5 facts that support it
- confidence: Your confidence (0-1) in this insight

Focus on "big picture" - what do these facts collectively tell us?"""

        questions_list = list(aggregated.facts_by_question.keys())
        content = f"""Research Session: {aggregated.session_id}

Total Facts Available: {aggregated.total_facts}
Analyzing Sample: {len(sampled_facts)} facts

Sampled Facts:
{facts_text}

Questions Addressed:
{questions_list}"""

        result = await self.llm.extract_structured(
            content=content,
            output_model=InsightsList,
            system_prompt=system_prompt,
            max_retries=2
        )
        
        if not result.success:
            logger.error(f"Failed to extract key insights: {result.error}")
            return self._fallback_insights(aggregated)
        
        return [
            KeyInsight(**i) for i in result.data.insights
        ]
    
    def _fallback_insights(
        self,
        aggregated: AggregatedFacts
    ) -> List[KeyInsight]:
        return [
            KeyInsight(
                insight=f"Analyzed {aggregated.total_facts} facts across {len(aggregated.facts_by_question)} research questions",
                supporting_facts=[
                    f"Top domain: {max(aggregated.domain_counts, key=aggregated.domain_counts.__getitem__)}",
                    f"Average confidence: {aggregated.avg_confidence:.2f}"
                ],
                confidence=aggregated.avg_confidence
            )
        ]
    
    def generate_markdown_report(
        self,
        session_id: str,
        report: Optional[SynthesizedReport] = None
    ) -> str:
        if report is None:
            logger.info(f"Loading report from database for session {session_id}")
            report = asyncio.run(self.synthesize_report(session_id))
        
        template = self.jinja_env.get_template('reports/full_report.md.jinja2')
        
        context = {
            'session_id': session_id,
            'executive_summary': {
                'overview': report.executive_summary.overview,
                'primary_conclusions': report.executive_summary.primary_conclusions,
                'confidence': report.executive_summary.confidence_level
            },
            'sections': report.detailed_findings.sections,
            'key_insights': [
                {
                    'insight': i.insight,
                    'confidence': i.confidence,
                    'supporting_facts': i.supporting_facts
                }
                for i in report.key_insights
            ],
            'domain_counts': report.metadata.get('domain_counts', {}),
            'total_facts': report.metadata.get('total_facts', 0),
            'unique_sources': report.metadata.get('unique_sources', 0),
            'avg_confidence': report.metadata.get('avg_confidence', 0.0),
            'generated_at': report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        markdown = template.render(**context)
        
        logger.info(f"Generated markdown report for session {session_id} ({len(markdown)} chars)")
        return markdown
