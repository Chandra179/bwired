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
  # Basic usage with config file
  python -m markdown_chunker.vectorize --input report.md --config vectorize.yaml
  
  # Override document title
  python -m markdown_chunker.vectorize --input report.md --config vectorize.yaml --document-title "Q4 Report"
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to input markdown file'
    )
    
    parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to YAML config file (vectorize.yaml)'
    )
    
    parser.add_argument(
        '--document-id',
        help='Document ID (defaults to filename without extension)'
    )
    
    parser.add_argument(
        '--document-title',
        help='Document title (defaults to filename)'
    )
    
    return parser.parse_args()


def load_configurations(config_path):
    """Load configurations from config file"""
    logger.info(f"Loading config from: {config_path}")
    config_data = load_config_file(config_path)
    
    # Create embedding config
    embedding_config = EmbeddingConfig(
        model_name=config_data.get('model_name', 'BAAI/bge-base-en-v1.5'),
        max_token_limit=config_data.get('max_token_limit', 512),
        target_chunk_size=config_data.get('target_chunk_size', 400),
        min_chunk_size=config_data.get('min_chunk_size', 100),
        overlap_tokens=config_data.get('overlap_tokens', 50),
        device=config_data.get('device', 'cpu')
    )
    
    # Create Qdrant config
    qdrant_config = QdrantConfig(
        url=config_data.get('qdrant_url', 'http://localhost:6333'),
        collection_name=config_data.get('collection_name', 'markdown_chunks'),
        api_key=config_data.get('api_key')
    )
    
    # Get logging config
    log_level = config_data.get('log_level', 'INFO')
    log_file = config_data.get('log_file')
    
    return embedding_config, qdrant_config, log_level, log_file


def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        # Load configurations
        embedding_config, qdrant_config, log_level, log_file = load_configurations(args.config)
        
        # Setup logging
        setup_logging(log_level, log_file)
        
        logger.info("Starting markdown vectorization pipeline")
        logger.info(f"Input file: {args.input}")
        logger.info(f"Model: {embedding_config.model_name}")
        logger.info(f"Target chunk size: {embedding_config.target_chunk_size} tokens")
        
        # Read markdown file
        logger.info("Reading markdown file...")
        content = read_markdown_file(args.input)
        file_size = Path(args.input).stat().st_size
        
        # Get document metadata
        document_id = get_document_id_from_path(args.input)
        document_title = Path(args.input).name
        
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