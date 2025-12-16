"""
Command-line interface for markdown chunking and embedding
"""
import argparse
import sys
import logging
from pathlib import Path

from .config import EmbeddingConfig, QdrantConfig
from .tokenizer_utils import TokenCounter
from .chunker import MarkdownChunker
from .embedder import EmbeddingGenerator
from .storage import QdrantStorage
from .utils import (
    setup_logging, 
    read_markdown_file, 
    load_config_file,
    get_document_id_from_path,
    print_summary
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Chunk markdown documents and store embeddings in Qdrant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python -m markdown_chunker.cli --input report.md --qdrant-url http://localhost:6333
  
  # With custom collection name
  python -m markdown_chunker.cli --input report.md --collection my_docs
  
  # With config file overrides
  python -m markdown_chunker.cli --input report.md --config config.yaml
  
  # With API key for remote Qdrant
  python -m markdown_chunker.cli --input report.md --qdrant-url https://xyz.cloud.qdrant.io --api-key YOUR_KEY
  
  # With GPU acceleration
  python -m markdown_chunker.cli --input report.md --device cuda
  
  # Search for similar chunks
  python -m markdown_chunker.cli --search "what's the cause of the political tension" --collection my_docs
  
  # Search with limit and document filter
  python -m markdown_chunker.cli --search "climate change" --search-limit 10 --filter-document report_2024
        """
    )
    
    # Input - now optional (required only if not searching)
    parser.add_argument(
        '--input', '-i',
        help='Path to input markdown file'
    )
    
    # Search functionality
    parser.add_argument(
        '--search', '-s',
        help='Search query text'
    )
    
    parser.add_argument(
        '--search-limit',
        type=int,
        default=5,
        help='Maximum number of search results (default: 5)'
    )
    
    parser.add_argument(
        '--filter-document',
        help='Filter search results by document ID'
    )
    
    # Qdrant configuration
    parser.add_argument(
        '--qdrant-url',
        default='http://localhost:6333',
        help='Qdrant server URL (default: http://localhost:6333)'
    )
    
    parser.add_argument(
        '--collection-name',
        default='markdown_chunks',
        help='Qdrant collection name (default: markdown_chunks)'
    )
    
    parser.add_argument(
        '--api-key',
        help='Qdrant API key (for cloud instances)'
    )
    
    # Embedding configuration
    parser.add_argument(
        '--model',
        default='BAAI/bge-base-en-v1.5',
        help='HuggingFace model name (default: BAAI/bge-base-en-v1.5)'
    )
    
    parser.add_argument(
        '--device',
        default='cpu',
        choices=['cpu', 'cuda'],
        help='Device for embedding generation (default: cpu)'
    )
    
    # Chunking parameters
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=512,
        help='Maximum token limit (default: 512)'
    )
    
    parser.add_argument(
        '--target-chunk-size',
        type=int,
        default=400,
        help='Target chunk size in tokens (default: 400)'
    )
    
    parser.add_argument(
        '--min-chunk-size',
        type=int,
        default=100,
        help='Minimum chunk size in tokens (default: 100)'
    )
    
    parser.add_argument(
        '--overlap-tokens',
        type=int,
        default=50,
        help='Number of overlap tokens between chunks (default: 50)'
    )
    
    # Document metadata
    parser.add_argument(
        '--document-id',
        help='Document ID (defaults to filename without extension)'
    )
    
    parser.add_argument(
        '--document-title',
        help='Document title (defaults to filename)'
    )
    
    # Config file
    parser.add_argument(
        '--config',
        help='Path to YAML config file (overrides defaults)'
    )
    
    # Logging
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Path to log file (optional)'
    )
    
    # Actions
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse and chunk without storing in Qdrant'
    )
    
    parser.add_argument(
        '--show-collection-info',
        action='store_true',
        help='Show Qdrant collection info and exit'
    )
    
    return parser.parse_args()


def load_configurations(args):
    """Load and merge configurations from args and config file"""
    
    # Load config file if provided
    config_overrides = {}
    if args.config:
        logger.info(f"Loading config from: {args.config}")
        config_overrides = load_config_file(args.config)
    
    # Create embedding config
    embedding_config = EmbeddingConfig(
        model_name=config_overrides.get('model_name', args.model),
        max_token_limit=config_overrides.get('max_token_limit', args.max_tokens),
        target_chunk_size=config_overrides.get('target_chunk_size', args.target_chunk_size),
        min_chunk_size=config_overrides.get('min_chunk_size', args.min_chunk_size),
        overlap_tokens=config_overrides.get('overlap_tokens', args.overlap_tokens),
        device=config_overrides.get('device', args.device)
    )
    
    # Create Qdrant config
    qdrant_config = QdrantConfig(
        url=config_overrides.get('qdrant_url', args.qdrant_url),
        collection_name=config_overrides.get('collection_name', args.collection_name),
        api_key=config_overrides.get('api_key', args.api_key)
    )
    
    return embedding_config, qdrant_config


def perform_search(args, embedding_config, qdrant_config):
    """Perform search operation"""
    logger.info(f"Searching for: '{args.search}'")
    
    # Initialize embedder
    logger.info("Initializing embedding model...")
    embedder = EmbeddingGenerator(embedding_config)
    
    # Generate query embedding
    logger.info("Generating query embedding...")
    query_embedding = embedder.generate_embeddings([args.search])[0]
    
    # Initialize storage
    storage = QdrantStorage(qdrant_config, embedder.get_embedding_dimension())
    
    # Build filters if document filter is specified
    filters = None
    if args.filter_document:
        filters = {
            "must": [
                {
                    "key": "document_id",
                    "match": {"value": args.filter_document}
                }
            ]
        }
        logger.info(f"Filtering by document: {args.filter_document}")
    
    # Perform search
    logger.info(f"Searching (limit: {args.search_limit})...")
    results = storage.search(
        query_embedding=query_embedding,
        limit=args.search_limit,
        filters=filters
    )
    
    # Display results
    if not results:
        print("\nNo results found.")
        return 0
    
    print(f"\n{'='*80}")
    print(f"Found {len(results)} results for: '{args.search}'")
    print(f"{'='*80}\n")
    
    for i, result in enumerate(results, 1):
        score = result['score']
        content = result['content']
        metadata = result['metadata']
        
        print(f"Result {i} (Score: {score:.4f})")
        print(f"Document: {metadata.get('document_title', 'N/A')} (ID: {metadata.get('document_id', 'N/A')})")
        if metadata.get('heading'):
            print(f"Heading: {metadata['heading']}")
        print(f"Chunk: {metadata.get('chunk_index', 'N/A')}/{metadata.get('total_chunks', 'N/A')}")
        print(f"\nContent:\n{content}")
        print(f"{'-'*80}\n")
    
    return 0


def main():
    """Main entry point"""
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    try:
        # Load configurations
        embedding_config, qdrant_config = load_configurations(args)
        
        # Handle search mode
        if args.search:
            return perform_search(args, embedding_config, qdrant_config)
        
        # Validate input is provided for non-search operations
        if not args.input and not args.show_collection_info:
            logger.error("--input is required when not using --search or --show-collection-info")
            print("Error: --input is required when not using --search", file=sys.stderr)
            return 1
        
        logger.info("Starting markdown chunking pipeline")
        logger.info(f"Input file: {args.input}")
        logger.info(f"Model: {embedding_config.model_name}")
        logger.info(f"Target chunk size: {embedding_config.target_chunk_size} tokens")
        
        # Show collection info if requested
        if args.show_collection_info:
            storage = QdrantStorage(qdrant_config, embedding_config.model_dim)
            info = storage.get_collection_info()
            print("\nCollection Information:")
            print(f"  Name: {info['name']}")
            print(f"  Vectors: {info['vectors_count']}")
            print(f"  Dimension: {info['vector_size']}")
            print(f"  Distance: {info['distance']}")
            return 0
        
        # Read markdown file
        logger.info("Reading markdown file...")
        content = read_markdown_file(args.input)
        file_size = Path(args.input).stat().st_size
        
        # Get document metadata
        document_id = args.document_id or get_document_id_from_path(args.input)
        document_title = args.document_title or Path(args.input).name
        
        # Initialize components
        logger.info("Initializing tokenizer...")
        token_counter = TokenCounter(embedding_config.model_name)
        
        logger.info("Initializing chunker...")
        chunker = MarkdownChunker(embedding_config, token_counter)
        
        # Parse and chunk document
        logger.info("Parsing and chunking document...")
        chunks = chunker.chunk_document(content, document_id, document_title)
        
        if not chunks:
            logger.warning("No chunks generated from document")
            return 1
        
        # Calculate statistics
        total_tokens = sum(chunk.token_count for chunk in chunks)
        num_elements = len(chunker.parser.parse(content))
        
        # Print summary
        print_summary(document_id, num_elements, len(chunks), total_tokens, file_size)
        
        if args.dry_run:
            logger.info("Dry run mode - skipping embedding and storage")
            print("Dry run complete. No data stored.")
            return 0
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embedder = EmbeddingGenerator(embedding_config)
        
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = embedder.generate_embeddings(chunk_texts)
        
        # Store in Qdrant
        logger.info("Storing in Qdrant...")
        storage = QdrantStorage(qdrant_config, embedder.get_embedding_dimension())
        storage.store_chunks(chunks, embeddings, document_id, document_title)
        
        logger.info("Pipeline completed successfully!")
        print(f"\n✓ Successfully processed and stored {len(chunks)} chunks")
        print(f"  Collection: {qdrant_config.collection_name}")
        print(f"  Document ID: {document_id}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())