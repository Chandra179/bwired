import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime

from internal.config import CrawlingConfig
from internal.research.web_crawler import WebCrawler
from internal.storage.postgres_client import PostgresClient

if TYPE_CHECKING:
    from internal.chunkers.base_chunker import BaseDocumentChunker
    from internal.embedding.dense_embedder import DenseEmbedder
    from internal.embedding.sparse_embedder import SparseEmbedder
    from internal.storage.qdrant_client import QdrantClient


logger = logging.getLogger(__name__)


@dataclass
class CrawlProgress:
    """Tracks crawling progress for a session."""
    session_id: str
    total_urls: int
    crawled_urls: int = 0
    failed_urls: int = 0
    skipped_duplicates: int = 0
    chunks_processed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def completion_rate(self) -> float:
        """Calculate completion percentage."""
        if self.total_urls == 0:
            return 0.0
        return (self.crawled_urls + self.failed_urls + self.skipped_duplicates) / self.total_urls
    
    @property
    def success_rate(self) -> float:
        """Calculate success percentage among attempted crawls."""
        attempted = self.crawled_urls + self.failed_urls
        if attempted == 0:
            return 0.0
        return self.crawled_urls / attempted


class CrawlOrchestrator:
    """Orchestrates web crawling with parallel processing and progress tracking."""
    
    def __init__(
        self,
        config: CrawlingConfig,
        postgres_client: PostgresClient,
        chunker: 'BaseDocumentChunker',
        dense_embedder: 'DenseEmbedder',
        sparse_embedder: 'SparseEmbedder',
        qdrant_client: 'QdrantClient'
    ):
        self.config = config
        self.postgres_client = postgres_client
        self.chunker = chunker
        self.dense_embedder = dense_embedder
        self.sparse_embedder = sparse_embedder
        self.qdrant_client = qdrant_client
        self._rate_limiter = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
    async def crawl_batch(
        self,
        session_id: str,
        urls: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> CrawlProgress:
        """
        Crawl a batch of URLs with parallel processing.
        
        Args:
            session_id: Research session ID
            urls: List of URL dictionaries with metadata
            batch_size: Number of URLs to process in each batch
            
        Returns:
            CrawlProgress object with crawling statistics
        """
        # Sort URLs by relevance score (highest first)
        prioritized_urls = self._prioritize_urls(urls)
        
        progress = CrawlProgress(
            session_id=session_id,
            total_urls=len(prioritized_urls),
            start_time=datetime.now()
        )
        
        logger.info(f"Starting crawl batch for session {session_id}: {len(prioritized_urls)} URLs")
        
        # Process URLs in batches to avoid overwhelming the system
        for i in range(0, len(prioritized_urls), batch_size):
            batch = prioritized_urls[i:i + batch_size]
            
            # Process batch with controlled concurrency
            batch_tasks = []
            for url_data in batch:
                task = self._crawl_single_url(session_id, url_data, progress)
                batch_tasks.append(task)
            
            # Wait for current batch to complete
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Update session progress
            self._update_session_progress(session_id, progress)
            
            # Brief pause between batches to be respectful
            if i + batch_size < len(prioritized_urls):
                await asyncio.sleep(1)
        
        progress.end_time = datetime.now()
        self._update_session_progress(session_id, progress, final=True)
        
        logger.info(
            f"Crawl batch completed for session {session_id}: "
            f"{progress.crawled_urls} crawled, {progress.failed_urls} failed, "
            f"{progress.skipped_duplicates} duplicates skipped"
        )
        
        return progress
    
    def _prioritize_urls(self, urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort URLs by relevance score and other quality factors.
        
        Args:
            urls: List of URL dictionaries
            
        Returns:
            Sorted list with highest priority URLs first
        """
        def url_priority(url_data: Dict[str, Any]) -> float:
            """Calculate priority score for a URL."""
            score = 0.0
            
            # Relevance score from search (40 points)
            relevance = url_data.get('relevance_score', 0)
            score += min(relevance * 0.4, 40)
            
            # Domain authority (30 points)
            domain = url_data.get('domain', '')
            if '.edu' in domain or '.ac.' in domain:
                score += 30
            elif '.gov' in domain:
                score += 30
            elif any(publisher in domain for publisher in ['nature.com', 'science.org', 'academic.oup.com']):
                score += 25
            
            # Content type preference (15 points)
            url = url_data.get('url', '')
            if url.endswith('.pdf'):
                score += 15
            elif 'arxiv.org' in url or 'pubmed.ncbi.nlm.nih.gov' in url:
                score += 15
            
            # Freshness (15 points) - if we have date info
            # This would require additional parsing in URLProcessor
            
            return score
        
        return sorted(urls, key=url_priority, reverse=True)
    
    async def _crawl_single_url(
        self,
        session_id: str,
        url_data: Dict[str, Any],
        progress: CrawlProgress
    ) -> None:
        """
        Crawl a single URL with rate limiting and error handling.
        
        Args:
            session_id: Research session ID
            url_data: URL dictionary with metadata
            progress: Progress tracking object
        """
        url = url_data.get('url')
        url_id = url_data.get('id')
        
        if not url or not url_id:
            logger.warning(f"Invalid URL data: {url_data}")
            progress.failed_urls += 1
            return
        
        # Apply rate limiting
        async with self._rate_limiter:
            try:
                async with WebCrawler(self.config) as crawler:
                    # Check for duplicate content before crawling
                    # (This would be enhanced if we had URL-based hashing)
                    
                    result = await crawler.crawl_url(url)
                    
                    if result['success']:
                        # Check for content duplicates
                        content_hash = result.get('content_hash')
                        if content_hash and self.postgres_client.check_content_hash(content_hash):
                            logger.info(f"Skipping duplicate content: {url}")
                            progress.skipped_duplicates += 1
                            self.postgres_client.update_url_status(url_id, 'skipped_duplicate')
                            return
                        
                        # Store the crawled content
                        doc_id = self.postgres_client.store_raw_document(
                            search_result_id=url_id,
                            content_type=result['content_type'],
                            raw_content=result['raw_content'],
                            content_hash=content_hash or ""
                        )
                        
                        # Update URL status
                        self.postgres_client.update_url_status(url_id, 'crawled')
                        
                        # Extract domain from URL
                        domain = self._extract_domain(url)
                        
                        # Get seed question from URL metadata
                        seed_question = url_data.get('seed_question', '')
                        
                        # Chunk the markdown content
                        chunks = self.chunker.chunk_document(
                            content=result['raw_content'],
                            document_id=doc_id
                        )
                        
                        # Generate embeddings
                        dense_vectors = self.dense_embedder.encode([c.content for c in chunks])
                        sparse_vectors = self.sparse_embedder.encode([c.content for c in chunks])
                        
                        # Store in session-specific Qdrant collection
                        collection_name = f"research_{session_id}"
                        chunks_stored = await self.qdrant_client.upsert_research_chunks(
                            collection_name=collection_name,
                            chunks=chunks,
                            dense_vectors=dense_vectors,
                            sparse_vectors=sparse_vectors,
                            document_id=doc_id,
                            session_id=session_id,
                            source_url=url,
                            domain=domain,
                            seed_question=seed_question,
                            crawl_timestamp=datetime.now().isoformat()
                        )
                        
                        # Update progress
                        progress.chunks_processed += chunks_stored
                        logger.debug(f"Stored {chunks_stored} chunks for: {url}")
                        
                        progress.crawled_urls += 1
                        logger.debug(f"Successfully crawled: {url} (doc_id: {doc_id})")
                        
                    else:
                        # Mark crawl as failed
                        error_msg = result.get('error', 'Unknown error')
                        self.postgres_client.mark_crawl_failed(url_id, error_msg)
                        progress.failed_urls += 1
                        logger.warning(f"Failed to crawl {url}: {error_msg}")
                        
            except Exception as e:
                # Handle unexpected errors
                self.postgres_client.mark_crawl_failed(url_id, str(e))
                progress.failed_urls += 1
                logger.error(f"Unexpected error crawling {url}: {str(e)}")
    
    def _update_session_progress(
        self,
        session_id: str,
        progress: CrawlProgress,
        final: bool = False
    ) -> None:
        """
        Update session progress in database.
        
        Args:
            session_id: Research session ID
            progress: Current progress object
            final: Whether this is the final progress update
        """
        progress_data = {
            'urls_found': progress.total_urls,
            'urls_crawled': progress.crawled_urls,
            'urls_failed': progress.failed_urls,
            'urls_skipped': progress.skipped_duplicates,
            'completion_rate': progress.completion_rate,
            'success_rate': progress.success_rate
        }
        
        if final:
            status = 'processing'  # Move to next phase after crawling
            if progress.end_time and progress.start_time:
                duration = (progress.end_time - progress.start_time).total_seconds()
                progress_data['crawl_duration_seconds'] = duration
        else:
            status = 'crawling'
        
        self.postgres_client.update_session_status(
            session_id=session_id,
            status=status,
            progress=progress_data
        )
    
    def get_crawl_statistics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get crawling statistics for a session.
        
        Args:
            session_id: Research session ID
            
        Returns:
            Dictionary with crawling statistics or None if not found
        """
        session_info = self.postgres_client.get_session_info(session_id)
        if not session_info:
            return None
        
        progress = session_info.get('progress', {})
        
        return {
            'session_id': session_id,
            'status': session_info.get('status'),
            'urls_found': progress.get('urls_found', 0),
            'urls_crawled': progress.get('urls_crawled', 0),
            'urls_failed': progress.get('urls_failed', 0),
            'urls_skipped': progress.get('urls_skipped', 0),
            'completion_rate': progress.get('completion_rate', 0.0),
            'success_rate': progress.get('success_rate', 0.0),
            'crawl_duration_seconds': progress.get('crawl_duration_seconds')
        }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return 'unknown'