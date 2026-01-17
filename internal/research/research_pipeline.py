"""
Research pipeline orchestrating the complete deep research workflow.

Coordinates: template selection -> search -> URL processing -> crawling ->
content processing -> retrieval -> fact extraction -> storage.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from internal.config import ResearchConfig, Config
from internal.storage.postgres_client import PostgresClient
from internal.storage.qdrant_client import QdrantClient
from internal.research.models import ResearchTemplate
from internal.research.template_manager import TemplateManager
from internal.research.search_orchestrator import SearchOrchestrator
from internal.url_processing import URLProcessor
from internal.research.crawl_orchestrator import CrawlOrchestrator
from internal.research.research_retriever import ResearchRetriever, RetrievedChunk
from internal.extraction import FactExtractor, ChunkWithMetadata
from internal.research.synthesizer import ResearchSynthesizer

if TYPE_CHECKING:
    from internal.chunkers.base_chunker import BaseDocumentChunker
    from internal.embedding.dense_embedder import DenseEmbedder
    from internal.embedding.sparse_embedder import SparseEmbedder

logger = logging.getLogger(__name__)


@dataclass
class ResearchProgress:
    """Comprehensive progress tracking for research pipeline."""
    session_id: str
    status: str  # 'started', 'searching', 'crawling', 'processing', 'extracting', 'completed', 'failed'
    
    # Search phase
    total_queries: int = 0
    completed_queries: int = 0
    urls_found: int = 0
    
    # Crawling phase
    urls_to_crawl: int = 0
    urls_crawled: int = 0
    urls_failed: int = 0
    
    # Processing phase
    chunks_processed: int = 0
    
    # Extraction phase
    chunks_for_extraction: int = 0
    facts_extracted: int = 0
    extraction_failures: int = 0
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "status": self.status,
            "total_queries": self.total_queries,
            "completed_queries": self.completed_queries,
            "urls_found": self.urls_found,
            "urls_to_crawl": self.urls_to_crawl,
            "urls_crawled": self.urls_crawled,
            "urls_failed": self.urls_failed,
            "chunks_processed": self.chunks_processed,
            "chunks_for_extraction": self.chunks_for_extraction,
            "facts_extracted": self.facts_extracted,
            "extraction_failures": self.extraction_failures,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message
        }


@dataclass
class ResearchResult:
    """Final result from a research pipeline run."""
    session_id: str
    success: bool
    progress: ResearchProgress
    facts: List[Dict[str, Any]]
    has_report: bool = False
    error: Optional[str] = None
    
    def get_report(self, synthesizer: ResearchSynthesizer) -> str:
        """Generate full markdown report"""
        import asyncio
        report = asyncio.run(synthesizer.synthesize_report(self.session_id))
        return synthesizer.generate_markdown_report(self.session_id, report)


class ResearchPipeline:
    """
    Orchestrates the complete deep research workflow.
    
    Pipeline stages:
    1. Template selection (auto or manual)
    2. Search execution (using seed questions)
    3. URL scoring and deduplication
    4. Web crawling (prioritized batch)
    5. Content processing (chunking + embedding)
    6. Retrieval for each seed question
    7. Fact extraction
    8. Fact storage
    """
    
    def __init__(
        self,
        config: Config,
        postgres_client: PostgresClient,
        qdrant_client: QdrantClient,
        chunker: 'BaseDocumentChunker',
        dense_embedder: 'DenseEmbedder',
        sparse_embedder: 'SparseEmbedder',
        reranker: Optional[Any] = None,
        synthesizer: Optional[ResearchSynthesizer] = None
    ):
        """
        Initialize the research pipeline with all required components.
        
        Args:
            config: Full application configuration
            postgres_client: Database client
            qdrant_client: Vector store client
            chunker: Document chunker
            dense_embedder: Dense embedding model
            sparse_embedder: Sparse embedding model
            reranker: Optional reranker model
            synthesizer: Optional report synthesizer
        """
        self.config = config
        if config.research is None:
            raise ValueError("research config is required for ResearchPipeline")
        self.research_config = config.research
        self.postgres_client = postgres_client
        self.qdrant_client = qdrant_client
        self.chunker = chunker
        self.dense_embedder = dense_embedder
        self.sparse_embedder = sparse_embedder
        self.reranker = reranker
        self.synthesizer = synthesizer or self._create_synthesizer()
        
        # Initialize sub-components
        self.template_manager = TemplateManager(postgres_client)
        self.search_orchestrator = SearchOrchestrator(self.research_config.searxng)
        self.url_processor = URLProcessor()
        self.crawl_orchestrator = CrawlOrchestrator(
            config=self.research_config.crawling,
            postgres_client=postgres_client,
            chunker=chunker,
            dense_embedder=dense_embedder,
            sparse_embedder=sparse_embedder,
            qdrant_client=qdrant_client
        )
        
        # Retriever and extractor initialized per-session
        self._retriever: Optional[ResearchRetriever] = None
        self._extractor: Optional[FactExtractor] = None
        
        logger.info("Initialized ResearchPipeline")
    
    def _create_synthesizer(self) -> ResearchSynthesizer:
        """Create synthesizer if not provided"""
        from internal.research.synthesizer import ResearchSynthesizer
        from internal.llm import create_llm_client
        
        return ResearchSynthesizer(
            postgres_client=self.postgres_client,
            llm_client=create_llm_client(self.research_config.synthesis.llm),
            config=self.research_config.synthesis
        )
    
    async def run(
        self,
        query: str,
        template_name: Optional[str] = None,
        max_urls: Optional[int] = None,
            generate_report: bool = True
    ) -> ResearchResult:
        """
        Execute complete research pipeline.

        Args:
            query: The research query/topic
            template_name: Optional template name (auto-selects if not provided)
            max_urls: Optional limit on URLs to crawl
            generate_report: Whether to generate report after extraction

        Returns:
            ResearchResult with extracted facts and progress info
        """
        progress = ResearchProgress(
            session_id="",
            status="started",
            start_time=datetime.now()
        )
        
        try:
            # 1. Template selection
            template = await self._select_template(query, template_name)
            if not template:
                raise ValueError("No suitable template found for query")
            
            logger.info(f"Using template: {template.name}")
            
            # 2. Create session
            session_id = self.postgres_client.create_session(
                query=query,
                template_id=template.id,
                status="searching"
            )
            progress.session_id = session_id
            
            logger.info(f"Created research session: {session_id}")
            
            # Initialize session-specific components
            self._init_session_components()
            
            # 3. Search phase
            progress.status = "searching"
            self._update_progress(session_id, progress)
            
            seed_questions = template.seed_questions or [query]
            progress.total_queries = len(seed_questions)
            
            all_urls = await self._execute_search(
                session_id=session_id,
                seed_questions=seed_questions,
                progress=progress
            )
            
            # 4. URL processing
            processed_urls = self._process_urls(all_urls, max_urls)
            progress.urls_to_crawl = len(processed_urls)
            
            # Store search results
            for seed_q, urls in processed_urls.items():
                self.postgres_client.store_search_results(
                    session_id=session_id,
                    seed_question=seed_q,
                    urls=urls
                )
            
            # 5. Crawling phase
            progress.status = "crawling"
            self._update_progress(session_id, progress)
            
            pending_urls = self.postgres_client.get_pending_urls(session_id)
            crawl_result = await self.crawl_orchestrator.crawl_batch(
                session_id=session_id,
                urls=pending_urls,
                batch_size=10
            )
            
            progress.urls_crawled = crawl_result.crawled_urls
            progress.urls_failed = crawl_result.failed_urls
            progress.chunks_processed = crawl_result.chunks_processed
            
            # 6. Processing phase (already done during crawling)
            progress.status = "processing"
            self._update_progress(session_id, progress)
            
            # 7. Retrieval and extraction phase
            progress.status = "extracting"
            self._update_progress(session_id, progress)
            
            await self._extract_facts(
                session_id=session_id,
                template=template,
                seed_questions=seed_questions,
                progress=progress
            )
            
            # 8. Synthesis
            if generate_report and self.synthesizer:
                progress.status = "synthesizing"
                self._update_progress(session_id, progress)
                
                try:
                    await self.synthesizer.synthesize_report(session_id)
                    result_has_report = True
                    logger.info(f"Report synthesized for session {session_id}")
                except Exception as e:
                    logger.error(f"Report synthesis failed: {e}")
                    result_has_report = False
            else:
                result_has_report = False
            
            # 9. Complete
            progress.status = "completed"
            progress.end_time = datetime.now()
            self._update_progress(session_id, progress)
            
            # Retrieve final facts
            facts = self.postgres_client.get_facts_by_session(
                session_id=session_id,
                min_confidence=self.research_config.extraction.confidence_threshold
            )
            
            logger.info(
                f"Research completed for session {session_id}: "
                f"{len(facts)} facts extracted"
            )
            
            return ResearchResult(
                session_id=session_id,
                success=True,
                progress=progress,
                facts=facts,
                has_report=result_has_report
            )
            
        except Exception as e:
            logger.error(f"Research pipeline failed: {e}")
            progress.status = "failed"
            progress.error_message = str(e)
            progress.end_time = datetime.now()
            
            if progress.session_id:
                self._update_progress(progress.session_id, progress)
            
            return ResearchResult(
                session_id=progress.session_id,
                success=False,
                progress=progress,
                facts=[],
                error=str(e)
            )
    
    async def run_async(
        self,
        query: str,
        template_name: Optional[str] = None,
        max_urls: Optional[int] = None
    ) -> str:
        """
        Start the research pipeline as a background task.
        
        Returns immediately with session_id for polling.
        
        Args:
            query: The research query/topic
            template_name: Optional template name
            max_urls: Optional URL limit
            
        Returns:
            Session ID for tracking progress
        """
        # Create session immediately
        template = await self._select_template(query, template_name)
        if not template:
            raise ValueError("No suitable template found for query")
        
        session_id = self.postgres_client.create_session(
            query=query,
            template_id=template.id,
            status="started"
        )
        
        # Schedule background task
        asyncio.create_task(
            self._run_background(session_id, query, template, max_urls)
        )
        
        return session_id
    
    async def _run_background(
        self,
        session_id: str,
        query: str,
        template: ResearchTemplate,
        max_urls: Optional[int]
    ) -> None:
        """Run the pipeline in background after session creation."""
        progress = ResearchProgress(
            session_id=session_id,
            status="searching",
            start_time=datetime.now()
        )
        
        try:
            self._init_session_components()
            
            # Search
            seed_questions = template.seed_questions or [query]
            progress.total_queries = len(seed_questions)
            
            all_urls = await self._execute_search(
                session_id=session_id,
                seed_questions=seed_questions,
                progress=progress
            )
            
            # Process URLs
            processed_urls = self._process_urls(all_urls, max_urls)
            progress.urls_to_crawl = len(processed_urls)
            
            for seed_q, urls in processed_urls.items():
                self.postgres_client.store_search_results(
                    session_id=session_id,
                    seed_question=seed_q,
                    urls=urls
                )
            
            # Crawl
            progress.status = "crawling"
            self._update_progress(session_id, progress)
            
            pending_urls = self.postgres_client.get_pending_urls(session_id)
            crawl_result = await self.crawl_orchestrator.crawl_batch(
                session_id=session_id,
                urls=pending_urls,
                batch_size=10
            )
            
            progress.urls_crawled = crawl_result.crawled_urls
            progress.urls_failed = crawl_result.failed_urls
            progress.chunks_processed = crawl_result.chunks_processed
            
            # Extract
            progress.status = "extracting"
            self._update_progress(session_id, progress)
            
            await self._extract_facts(
                session_id=session_id,
                template=template,
                seed_questions=seed_questions,
                progress=progress
            )
            
            # Complete
            progress.status = "completed"
            progress.end_time = datetime.now()
            self._update_progress(session_id, progress)
            
        except Exception as e:
            logger.error(f"Background research failed: {e}")
            progress.status = "failed"
            progress.error_message = str(e)
            progress.end_time = datetime.now()
            self._update_progress(session_id, progress)
    
    def _init_session_components(self) -> None:
        """Initialize components that need per-session setup."""
        self._retriever = ResearchRetriever(
            qdrant_client=self.qdrant_client,
            dense_embedder=self.dense_embedder,
            sparse_embedder=self.sparse_embedder,
            config=self.research_config.extraction,
            reranker=self.reranker,
            reranker_config=self.config.reranker
        )
        
        self._extractor = FactExtractor(
            config=self.research_config.extraction,
            postgres_client=self.postgres_client
        )
    
    async def _select_template(
        self,
        query: str,
        template_name: Optional[str]
    ) -> Optional[ResearchTemplate]:
        """Select or retrieve a template for the research."""
        if template_name:
            # Use specified template
            template_data = self.postgres_client.get_template_by_name(template_name)
            if template_data:
                return ResearchTemplate(
                    id=str(template_data['id']),
                    name=template_data['name'],
                    description=template_data['description'],
                    schema_json=template_data['schema_json'],
                    system_prompt=template_data.get('system_prompt'),
                    seed_questions=template_data.get('seed_questions')
                )
            else:
                logger.warning(f"Template '{template_name}' not found")
                return None
        else:
            # Auto-select based on query (synchronous method)
            result = self.template_manager.select_template(query)
            if result and result.template_id:
                template_data = self.postgres_client.get_template(result.template_id)
                if template_data:
                    return ResearchTemplate(
                        id=str(template_data['id']),
                        name=template_data['name'],
                        description=template_data['description'],
                        schema_json=template_data['schema_json'],
                        system_prompt=template_data.get('system_prompt'),
                        seed_questions=template_data.get('seed_questions')
                    )
            
            # Fall back to first available template
            templates = self.postgres_client.list_templates()
            if templates:
                t = templates[0]
                return ResearchTemplate(
                    id=str(t['id']),
                    name=t['name'],
                    description=t['description'],
                    schema_json=t['schema_json'],
                    system_prompt=t.get('system_prompt'),
                    seed_questions=t.get('seed_questions')
                )
            
            return None
    
    async def _execute_search(
        self,
        session_id: str,
        seed_questions: List[str],
        progress: ResearchProgress
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Execute search for all seed questions."""
        all_urls = {}
        
        for question in seed_questions:
            try:
                # search_orchestrator.search is synchronous
                results = self.search_orchestrator.search(
                    query=question,
                    max_results=self.research_config.searxng.max_results_per_query
                )
                
                all_urls[question] = results
                progress.completed_queries += 1
                progress.urls_found += len(results)
                
                self._update_progress(session_id, progress)
                
            except Exception as e:
                logger.error(f"Search failed for '{question}': {e}")
                all_urls[question] = []
        
        return all_urls
    
    def _process_urls(
        self,
        urls_by_question: Dict[str, List[Dict[str, Any]]],
        max_urls: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Process, score, and deduplicate URLs."""
        processed = {}
        seen_hashes = set()
        total_count = 0
        max_urls = max_urls or 50  # Default limit
        
        for question, urls in urls_by_question.items():
            question_urls = []
            
            for url_data in urls:
                if total_count >= max_urls:
                    break
                
                url = url_data.get('url', '')
                
                # Normalize and deduplicate
                normalized = self.url_processor.normalize_url(url)
                url_hash = self.url_processor.calculate_hash(normalized)
                
                if url_hash in seen_hashes:
                    continue
                
                seen_hashes.add(url_hash)
                
                # Score the URL
                title = url_data.get('title', '')
                score = self.url_processor.score_relevance(url, title, question)
                
                # Filter by relevance threshold
                if score >= self.research_config.crawling.relevance_threshold:
                    url_data['relevance_score'] = score
                    url_data['seed_question'] = question
                    question_urls.append(url_data)
                    total_count += 1
            
            if question_urls:
                processed[question] = question_urls
        
        # Apply domain limits
        flattened = [url for urls in processed.values() for url in urls]
        limited = self.url_processor.filter_by_domain_limits(
            flattened,
            max_per_domain=self.research_config.crawling.max_urls_per_domain
        )
        
        # Reconstruct by question
        result = {}
        for url in limited:
            q = url.get('seed_question', '')
            if q not in result:
                result[q] = []
            result[q].append(url)
        
        return result
    
    async def _extract_facts(
        self,
        session_id: str,
        template: ResearchTemplate,
        seed_questions: List[str],
        progress: ResearchProgress
    ) -> None:
        """Retrieve and extract facts for each seed question."""
        for question in seed_questions:
            try:
                # Retrieve relevant chunks
                result = await self._retriever.retrieve_for_question(
                    question=question,
                    session_id=session_id,
                    filter_by_seed_question=question
                )
                
                if not result.chunks:
                    logger.warning(f"No chunks found for question: {question}")
                    continue
                
                progress.chunks_for_extraction += len(result.chunks)
                
                # Convert to extraction format
                chunks_for_extraction = [
                    ChunkWithMetadata(
                        chunk_id=chunk.chunk_id,
                        content=chunk.content,
                        source_url=chunk.source_url,
                        seed_question=chunk.seed_question,
                        section_path=chunk.section_path
                    )
                    for chunk in result.chunks
                ]
                
                # Extract facts
                extraction_result = await self._extractor.extract_batch(
                    chunks=chunks_for_extraction,
                    template=template,
                    session_id=session_id
                )
                
                progress.facts_extracted += extraction_result.successful_extractions
                progress.extraction_failures += extraction_result.failed_extractions
                
                self._update_progress(session_id, progress)
                
            except Exception as e:
                logger.error(f"Extraction failed for question '{question}': {e}")
                progress.extraction_failures += 1
    
    def _update_progress(
        self,
        session_id: str,
        progress: ResearchProgress
    ) -> None:
        """Update session progress in database."""
        self.postgres_client.update_session_status(
            session_id=session_id,
            status=progress.status,
            progress=progress.to_dict(),
            error_message=progress.error_message
        )
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a research session."""
        return self.postgres_client.get_session_info(session_id)
    
    def get_session_facts(
        self,
        session_id: str,
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get extracted facts from a session."""
        threshold = min_confidence or self.research_config.extraction.confidence_threshold
        return self.postgres_client.get_facts_by_session(
            session_id=session_id,
            min_confidence=threshold
        )
