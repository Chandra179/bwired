import hashlib
import logging
from typing import Dict, Any
from urllib.parse import urlparse

import httpx
from crawl4ai import AsyncWebCrawler
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter

from internal.config import CrawlingConfig


logger = logging.getLogger(__name__)


class WebCrawler:
    """Handles web crawling and content extraction using Crawl4AI."""
    
    def __init__(self, config: CrawlingConfig):
        self.config = config
        self.converter = DocumentConverter()
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers={"User-Agent": self.config.user_agent}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    async def crawl_url(self, url: str) -> Dict[str, Any]:
        """
        Crawl a single URL and extract its content.
        
        Args:
            url: The URL to crawl
            
        Returns:
            Dictionary containing:
            - success: bool indicating if crawl succeeded
            - content_type: str ('html', 'pdf', 'error')
            - raw_content: str the extracted content
            - content_hash: str hash of the content
            - error: str error message if failed
        """
        try:
            # Use Crawl4AI for HTML content
            if url.lower().endswith('.pdf'):
                return await self._handle_pdf(url)
            else:
                return await self._handle_html(url)
                
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {str(e)}")
            return {
                "success": False,
                "content_type": "error",
                "raw_content": None,
                "content_hash": None,
                "error": str(e)
            }
    
    async def _handle_html(self, url: str) -> Dict[str, Any]:
        """Handle HTML content extraction using Crawl4AI."""
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=url,
                timeout=self.config.timeout,
                user_agent=self.config.user_agent
            )
            
            # Wait for the result to complete
            if hasattr(result, '__aiter__'):
                # If result is an async generator, consume it
                result = await result.__anext__()
            
            if not getattr(result, 'success', False):
                error_msg = getattr(result, 'error_message', 'Unknown Crawl4AI error')
                return {
                    "success": False,
                    "content_type": "error",
                    "raw_content": None,
                    "content_hash": None,
                    "error": f"Crawl4AI failed: {error_msg}"
                }
            
            # Extract main content using Crawl4AI's built-in content extraction
            content = getattr(result, 'cleaned_html', None) or getattr(result, 'html', '') or getattr(result, 'markdown', '')
            
            if not content:
                return {
                    "success": False,
                    "content_type": "error",
                    "raw_content": None,
                    "content_hash": None,
                    "error": "No content extracted from Crawl4AI"
                }
            
            # Convert to markdown using Docling for consistency
            try:
                doc_result = self.converter.convert_string(content, format=InputFormat.HTML)
                markdown_content = doc_result.document.export_to_markdown()
            except Exception as e:
                logger.warning(f"Failed to convert HTML to markdown: {e}")
                markdown_content = content
            
            content_hash = self._calculate_content_hash(markdown_content)
            
            return {
                "success": True,
                "content_type": "html",
                "raw_content": markdown_content,
                "content_hash": content_hash,
                "error": None
            }
    
    async def _handle_pdf(self, url: str) -> Dict[str, Any]:
        """Handle PDF content extraction."""
        if not self.session:
            # Create session if not available
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={"User-Agent": self.config.user_agent}
            )
        
        try:
            # Download PDF using httpx
            response = await self.session.get(url)
            response.raise_for_status()
            
            # Convert PDF to markdown using Docling
            import tempfile
            import os
            
            # Create temporary file for PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(response.content)
                tmp_file_path = tmp_file.name
            
            try:
                doc_result = self.converter.convert(tmp_file_path)
                markdown_content = doc_result.document.export_to_markdown()
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
            
            content_hash = self._calculate_content_hash(markdown_content)
            
            return {
                "success": True,
                "content_type": "pdf",
                "raw_content": markdown_content,
                "content_hash": content_hash,
                "error": None
            }
            
        except httpx.HTTPStatusError as e:
            status_code = getattr(e.response, 'status_code', 'Unknown')
            reason_phrase = getattr(e.response, 'reason_phrase', 'Unknown')
            error_msg = f"HTTP {status_code}: {reason_phrase}"
            logger.error(f"Failed to download PDF {url}: {error_msg}")
            return {
                "success": False,
                "content_type": "error",
                "raw_content": None,
                "content_hash": None,
                "error": error_msg
            }
        except Exception as e:
            logger.error(f"Failed to process PDF {url}: {str(e)}")
            return {
                "success": False,
                "content_type": "error",
                "raw_content": None,
                "content_hash": None,
                "error": str(e)
            }
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for duplicate detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def extract_content(self, html: str) -> str:
        """
        Extract main content from HTML, removing boilerplate.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Cleaned text content
        """
        # This is a simplified implementation
        # Crawl4AI already does content extraction, but this method
        # is kept for potential custom extraction logic
        return html
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid and accessible."""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)
        except Exception:
            return False