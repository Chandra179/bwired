import argparse
import asyncio
import sys
import logging

from .config_loader import ConfigurationLoader
from .display import SearchResultsDisplay

from ..embedding.embedder import EmbeddingGenerator
from ..storage.qdrant_storage import QdrantStorage
from ..logger import setup_logging

logger = logging.getLogger(__name__)


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
            embedding_config, qdrant_config, search_params, log_level = \
                self.config_loader.load_search_config(self.args.config)
            
            setup_logging(log_level)
            
            logger.info(f"Searching for: '{self.args.query}'")
            logger.info(f"Collection: {qdrant_config.collection_name}")
            
            logger.info("Initializing embedding model...")
            embedder = EmbeddingGenerator(embedding_config)
            
            logger.info("Generating query embedding...")
            query_embedding = embedder.generate_dense_embeddings([self.args.query])[0]
            
            storage = QdrantStorage(qdrant_config, embedder.get_embedding_dimension())
            
            logger.info(f"Searching (limit: {search_params['limit']})...")
            results = await storage.search(
                query_embedding=query_embedding,
                limit=search_params['limit'],
                score_threshold=search_params.get('score_threshold'),
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