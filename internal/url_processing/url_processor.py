import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlunparse
from hashlib import sha256
import re
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class URLProcessor:
    """Process, normalize, and score URLs for research relevance"""

    def __init__(self, trusted_domains_path: Optional[str] = None):
        """
        Initialize URL processor with trusted domain scores

        Args:
            trusted_domains_path: Path to JSON file with domain authority scores
        """
        if trusted_domains_path is None:
            trusted_domains_path = "internal/url_processing/trusted_domains.json"
        
        self.trusted_domains = self._load_trusted_domains(trusted_domains_path)
        logger.info(f"URLProcessor initialized with {len(self.trusted_domains['domains'])} trusted domains")

    def _load_trusted_domains(self, path: str) -> Dict[str, Any]:
        """
        Load trusted domain configuration from JSON file

        Args:
            path: Path to trusted_domains.json

        Returns:
            Dictionary with 'tlds' and 'domains' mappings
        """
        default_config = {
            "tlds": {".edu": 30, ".gov": 30, ".org": 10},
            "domains": {}
        }

        try:
            file_path = Path(path)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {
                        'tlds': config.get('tlds', default_config['tlds']),
                        'domains': config.get('domains', default_config['domains'])
                    }
        except Exception as e:
            logger.warning(f"Failed to load trusted domains from {path}: {e}")
        
        return default_config

    def normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing tracking params, standardizing format

        Args:
            url: Raw URL string

        Returns:
            Normalized URL string
        """
        try:
            parsed = urlparse(url)
            
            # Lowercase scheme and netloc
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            
            # Remove default port (80 for http, 443 for https)
            if (scheme == 'http' and netloc.endswith(':80')) or \
               (scheme == 'https' and netloc.endswith(':443')):
                netloc = netloc.rsplit(':', 1)[0]
            
            # Remove 'www.' prefix
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            
            # Remove tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'msclkid', '_ga', '_gl', 'ref', 'ref_source',
                'source', 'mc_cid', 'mc_eid', 'utm_source', 'utm_reader'
            }
            
            query_params = parse_qs(parsed.query)
            filtered_params = {
                k: v for k, v in query_params.items() 
                if k not in tracking_params
            }
            
            # Rebuild query string
            new_query = '&'.join(
                f"{k}={v[0]}" for k, v in filtered_params.items()
            ) if filtered_params else ''
            
            # Remove fragment (anchor)
            fragment = ''
            
            normalized = urlunparse((
                scheme,
                netloc,
                parsed.path,
                parsed.params,
                new_query,
                fragment
            ))
            
            # Remove trailing slash unless it's the root
            if normalized.endswith('/') and len(normalized) > len(f"{scheme}://{netloc}/"):
                normalized = normalized[:-1]
            
            return normalized

        except Exception as e:
            logger.warning(f"Failed to normalize URL '{url}': {e}")
            return url

    def calculate_hash(self, url: str) -> str:
        """
        Calculate SHA256 hash of normalized URL for deduplication

        Args:
            url: URL string (will be normalized internally)

        Returns:
            Hexadecimal hash string
        """
        normalized = self.normalize_url(url)
        return sha256(normalized.encode('utf-8')).hexdigest()

    def score_relevance(
        self,
        url: str,
        title: str,
        query: str,
        fetch_freshness: bool = False
    ) -> float:
        """
        Calculate relevance score for a URL based on multiple factors

        Scoring:
        - Query Match (0-40 pts): Keyword overlap in URL/title
        - Domain Authority (0-30 pts): TLD and domain reputation
        - Content Type (0-15 pts): PDFs, research papers get bonus
        - Freshness (0-15 pts): Recency (placeholder, implemented in Phase 4)

        Args:
            url: URL to score
            title: Page title
            query: Search query
            fetch_freshness: Whether to fetch and parse date metadata (future feature)

        Returns:
            Relevance score (0-100)
        """
        score = 0.0
        normalized_url = url.lower()
        normalized_title = title.lower()
        normalized_query = query.lower()
        
        # Query Match (0-40 points)
        query_score = self._score_query_match(
            normalized_url, normalized_title, normalized_query
        )
        score += query_score
        
        # Domain Authority (0-30 points)
        domain_score = self._score_domain_authority(url)
        score += domain_score
        
        # Content Type (0-15 points)
        content_score = self._score_content_type(url, title)
        score += content_score
        
        # Freshness (0-15 points) - placeholder for Phase 4
        freshness_score = 0.0
        if fetch_freshness:
            pass
        
        score = min(score, 100.0)
        
        logger.debug(
            f"Score {score:.1f} for URL {url[:50]}... "
            f"(query: {query_score}, domain: {domain_score}, "
            f"content: {content_score}, freshness: {freshness_score})"
        )
        
        return score

    def _score_query_match(
        self,
        url: str,
        title: str,
        query: str
    ) -> float:
        """
        Score query-term overlap in URL and title

        Args:
            url: Lowercase normalized URL
            title: Lowercase page title
            query: Lowercase search query

        Returns:
            Query match score (0-40)
        """
        # Extract meaningful terms from query (stop words removed)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
            'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
            'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }
        
        terms = [
            term for term in re.findall(r'\w+', query)
            if len(term) > 2 and term not in stop_words
        ]
        
        if not terms:
            return 0.0
        
        # Calculate term frequency in URL and title
        url_matches = sum(1 for term in terms if term in url)
        title_matches = sum(1 for term in terms if term in title)
        
        # Title matches are worth more
        score = (url_matches * 3) + (title_matches * 5)
        
        # Bonus for exact phrase match in title
        if query in title:
            score += 10
        
        return min(score, 40.0)

    def _score_domain_authority(self, url: str) -> float:
        """
        Score domain based on TLD and trusted domains list

        Args:
            url: URL string

        Returns:
            Domain authority score (0-30)
        """
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            
            # Check exact domain matches
            for domain, score in self.trusted_domains['domains'].items():
                if domain.lower() in netloc:
                    return float(score)
            
            # Check TLD matches
            for tld, score in self.trusted_domains['tlds'].items():
                if netloc.endswith(tld.lower()):
                    return float(score)
            
            # Base score for generic .com/net/etc
            common_tlds = ['.com', '.net', '.io', '.co']
            if any(netloc.endswith(tld) for tld in common_tlds):
                return 5.0
            
            return 0.0

        except Exception:
            return 0.0

    def _score_content_type(self, url: str, title: str) -> float:
        """
        Score based on content type indicators

        Args:
            url: URL string
            title: Page title

        Returns:
            Content type score (0-15)
        """
        score = 0.0
        
        # PDF bonus
        if url.lower().endswith('.pdf'):
            score += 10.0
        
        # Research indicators in URL or title
        research_keywords = [
            'journal', 'paper', 'research', 'study', 'publication',
            'arxiv', 'pubmed', 'proceedings', 'conference', 'thesis'
        ]
        
        combined_text = f"{url} {title}".lower()
        for keyword in research_keywords:
            if keyword in combined_text:
                score += 2.5
        
        return min(score, 15.0)

    def deduplicate_urls(self, url_list: List[str]) -> List[str]:
        """
        Remove duplicate URLs using hash-based deduplication

        Args:
            url_list: List of URLs to deduplicate

        Returns:
            Deduplicated list of URLs (first occurrence kept)
        """
        seen_hashes = set()
        unique_urls = []
        
        for url in url_list:
            url_hash = self.calculate_hash(url)
            if url_hash not in seen_hashes:
                seen_hashes.add(url_hash)
                unique_urls.append(url)
        
        duplicates_removed = len(url_list) - len(unique_urls)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate URLs")
        
        return unique_urls

    def filter_by_domain_limits(
        self,
        urls_with_scores: List[Dict[str, Any]],
        max_per_domain: int
    ) -> List[Dict[str, Any]]:
        """
        Enforce maximum URLs per domain

        Args:
            urls_with_scores: List of dicts with 'url' and 'relevance_score'
            max_per_domain: Maximum URLs to keep per domain

        Returns:
            Filtered list of URLs (highest scoring kept per domain)
        """
        domain_buckets = {}
        
        for item in urls_with_scores:
            url = item['url']
            try:
                domain = urlparse(url).netloc.lower()
            except:
                domain = 'unknown'
            
            if domain not in domain_buckets:
                domain_buckets[domain] = []
            domain_buckets[domain].append(item)
        
        filtered = []
        for domain, items in domain_buckets.items():
            # Sort by relevance score (descending)
            sorted_items = sorted(items, key=lambda x: x.get('relevance_score', 0), reverse=True)
            # Keep top N
            filtered.extend(sorted_items[:max_per_domain])
        
        # Re-sort by overall score
        filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        total_filtered = len(urls_with_scores) - len(filtered)
        if total_filtered > 0:
            logger.info(f"Filtered {total_filtered} URLs exceeding domain limit")
        
        return filtered

    def extract_domain(self, url: str) -> Optional[str]:
        """
        Extract domain from URL

        Args:
            url: URL string

        Returns:
            Domain string or None if parsing fails
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception as e:
            logger.warning(f"Failed to extract domain from '{url}': {e}")
            return None
