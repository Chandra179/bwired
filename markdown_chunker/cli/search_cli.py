import argparse
import asyncio
import sys
import logging

from .config_loader import ConfigurationLoader
from .display import SearchResultsDisplay

from ..embedding.dense_embedder import DenseEmbedder
from ..embedding.sparse_embedder import SparseEmbedder
from ..embedding.reranker import Reranker
from ..storage.qdrant_storage import QdrantStorage
from ..logger import setup_logging

logger = logging.getLogger(__name__)

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class SearchCommand:
    """Encapsulates search command logic"""
    
    def __init__(self, args):
        self.args = args
        self.config_loader = ConfigurationLoader()
        self.results_display = SearchResultsDisplay()
    
    async def execute(self) -> int:
        """
        Execute the search command
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            embedding_config, reranker_config, qdrant_config, search_params, log_level = \
                self.config_loader.load_search_config(self.args.config)
            
            setup_logging(log_level)
            
            logger.info(f"Searching for: '{self.args.query}'")
            logger.info(f"Collection: {qdrant_config.collection_name}")
            
            # Initialize dense embedder
            logger.info("Initializing dense embedding model...")
            dense_embedder = DenseEmbedder(embedding_config.dense)
            
            # Initialize sparse embedder
            logger.info("Initializing sparse embedding model...")
            sparse_embedder = SparseEmbedder(embedding_config.sparse)
            
            # Initialize reranker
            logger.info("Initializing reranker model...")
            reranker = Reranker(reranker_config)
            
            # Generate query embeddings
            logger.info("Generating query embeddings...")
            query_dense = dense_embedder.encode([self.args.query])[0]
            query_sparse = sparse_embedder.encode([self.args.query])[0]
            
            # Initialize storage
            storage = QdrantStorage(qdrant_config, dense_embedder.get_dimension())
            
            # Perform search with reranking
            logger.info(f"Searching (limit: {search_params['limit']})...")
            results = await storage.search(
                query_text=self.args.query,
                query_dense_embedding=query_dense,
                query_sparse_embedding=query_sparse,
                reranker=reranker,
                limit=search_params['limit'],
            )
            
            self.results_display.display_results(self.args.query, results)
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            print(f"\n✗ Error: {e}", file=sys.stderr)
            return 1


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Search for similar chunks in Qdrant vector database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic search
  python -m markdown_chunker.search --config search.yaml --query "what is the political situation"
  
  # Search with custom query
  python -m markdown_chunker.search -c search.yaml -q "climate change impacts"
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to YAML config file (search.yaml)'
    )
    
    parser.add_argument(
        '--query', '-q',
        required=True,
        help='Search query text'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    command = SearchCommand(args)
    return asyncio.run(command.execute())


if __name__ == '__main__':
    sys.exit(main())