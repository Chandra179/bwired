import argparse
import asyncio
import sys
import logging

from .config import EmbeddingConfig, QdrantConfig
from .embedder import EmbeddingGenerator
from .storage import QdrantStorage
from .utils import setup_logging, load_config_file

logger = logging.getLogger(__name__)


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


def load_configurations(config_path):
    """Load configurations from config file"""
    logger.info(f"Loading config from: {config_path}")
    config_data = load_config_file(config_path)
    
    # Create embedding config (for query embedding)
    embedding_config = EmbeddingConfig(
        model_name=config_data.get('model_name', 'BAAI/bge-base-en-v1.5'),
        max_token_limit=config_data.get('max_token_limit', 512),
        device=config_data.get('device', 'cpu')
    )
    
    # Create Qdrant config
    qdrant_config = QdrantConfig(
        url=config_data.get('qdrant_url', 'http://localhost:6333'),
        collection_name=config_data.get('collection_name', 'markdown_chunks'),
    )
    
    # Get search parameters
    search_params = {
        'limit': config_data.get('search_limit', 5),
        'score_threshold': config_data.get('score_threshold'),
        'filter_document': config_data.get('filter_document'),
        'filter_heading': config_data.get('filter_heading')
    }
    
    # Get logging config
    log_level = config_data.get('log_level', 'INFO')
    
    return embedding_config, qdrant_config, search_params, log_level


def build_filters(search_params):
    """Build Qdrant filters from search parameters"""
    filters = {"must": []}
    
    if search_params.get('filter_document'):
        filters["must"].append({
            "key": "document_id",
            "match": {"value": search_params['filter_document']}
        })
    
    if search_params.get('filter_heading'):
        filters["must"].append({
            "key": "heading",
            "match": {"value": search_params['filter_heading']}
        })
    
    return filters if filters["must"] else None


def display_results(query, results, show_metadata=True):
    """Display search results in a formatted way"""
    if not results:
        print("\nNo results found.")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(results)} results for: '{query}'")
    print(f"{'='*80}\n")
    
    for i, result in enumerate(results, 1):
        score = result['score']
        content = result['content']
        metadata = result['metadata']
        
        print(f"Result {i} (Score: {score:.4f})")
        
        if show_metadata:
            print(f"Document: {metadata.get('document_title', 'N/A')} (ID: {metadata.get('document_id', 'N/A')})")
            
            if metadata.get('heading'):
                print(f"Heading: {metadata['heading']}")
            
            if metadata.get('section_path'):
                print(f"Section: {metadata['section_path']}")
            
        print(f"\nContent:\n{content}")
        print(f"{'-'*80}\n")


async def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        embedding_config, qdrant_config, search_params, log_level = load_configurations(args.config)
        
        setup_logging(log_level)
        
        logger.info(f"Searching for: '{args.query}'")
        logger.info(f"Collection: {qdrant_config.collection_name}")
        
        logger.info("Initializing embedding model...")
        embedder = EmbeddingGenerator(embedding_config)
        
        logger.info("Generating query embedding...")
        query_embedding = embedder.generate_embeddings([args.query])[0]
        
        storage = QdrantStorage(qdrant_config, embedder.get_embedding_dimension())
        
        filters = build_filters(search_params)
        if filters:
            logger.info(f"Applied filters: {filters}")
        
        logger.info(f"Searching (limit: {search_params['limit']})...")
        results = await storage.search(
            query_embedding=query_embedding,
            limit=search_params['limit'],
            score_threshold=search_params.get('score_threshold'),
            filters=filters
        )
        
        display_results(args.query, results)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    asyncio.run(main())