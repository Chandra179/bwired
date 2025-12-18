"""
Command-line interface for RAG-optimized markdown chunking and embedding
"""
import argparse
import sys
import logging
import asyncio
from pathlib import Path

from .config import RAGChunkingConfig, ChunkingConfig, ContextConfig, EmbeddingConfig, QdrantConfig
from .semantic_chunker import SemanticChunker
from .embedder import EmbeddingGenerator
from .storage import QdrantStorage
from .utils import (
    setup_logging, 
    read_markdown_file, 
    load_config_file,
    get_document_id_from_path,
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Chunk markdown documents with RAG optimization and store embeddings in Qdrant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with config file
  python -m markdown_chunker.vectorize --input report.md --config vectorize.yaml
  
  # Override document title
  python -m markdown_chunker.vectorize --input report.md --config vectorize.yaml --document-title "Q4 Report"
  
  # Process with custom document ID
  python -m markdown_chunker.vectorize -i report.md -c vectorize.yaml --document-id "q4_2024"
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
    
    chunking_config = ChunkingConfig(
        target_chunk_size=config_data.get('target_chunk_size', 500),
        keep_tables_intact=config_data.get('keep_tables_intact', True),
        keep_code_blocks_intact=config_data.get('keep_code_blocks_intact', True),
        keep_list_items_together=config_data.get('keep_list_items_together', True),
        use_sentence_boundaries=config_data.get('use_sentence_boundaries', True),
    )
    
    context_config = ContextConfig(
        include_header_path=config_data.get('include_header_path', True),
    )
    
    embedding_config = EmbeddingConfig(
        model_name=config_data.get('model_name', 'BAAI/bge-base-en-v1.5'),
        model_dim=config_data.get('model_dim', 768),
        max_token_limit=config_data.get('max_token_limit', 512),
        device=config_data.get('device', 'cpu'),
        batch_size=config_data.get('embedding_batch_size', 128),
        use_fp16=config_data.get('use_fp16', True),
        show_progress_bar=config_data.get('show_progress_bar', False)
    )
    
    rag_config = RAGChunkingConfig(
        chunking=chunking_config,
        context=context_config,
        embedding=embedding_config
    )
    
    qdrant_config = QdrantConfig(
        url=config_data.get('qdrant_url', 'http://localhost:6333'),
        collection_name=config_data.get('collection_name', 'markdown_chunks'),
        distance_metric=config_data.get('distance_metric', 'Cosine'),
        grpc_port=config_data.get('grpc_port', 6334),
        storage_batch_size=config_data.get('storage_batch_size', 500)
    )
    
    # Get logging config
    log_level = config_data.get('log_level', 'INFO')
    
    return rag_config, qdrant_config, log_level


def print_chunk_statistics(chunks):
    """Print statistics about generated chunks"""
    if not chunks:
        return
    
    chunk_types = {}
    total_tokens = 0
    multi_repr_count = 0
    entity_count = 0
    
    for chunk in chunks:
        chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
        total_tokens += chunk.token_count
    
    print(f"\nChunk Statistics:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Average tokens/chunk: {total_tokens / len(chunks):.1f}")
    
    print(f"\n  Chunk types:")
    for chunk_type, count in sorted(chunk_types.items()):
        print(f"    {chunk_type}: {count}")
    
    print(f"\n  RAG features:")
    print(f"    Chunks with multi-representation: {multi_repr_count}")
    print(f"    Chunks with entities: {entity_count}")


async def async_main(args):
    """Main async entry point"""
    try:
        # Load configurations
        rag_config, qdrant_config, log_level = load_configurations(args.config)
        
        # Setup logging
        setup_logging(log_level)
        
        logger.info("=" * 80)
        logger.info("Starting RAG-optimized markdown vectorization pipeline (OPTIMIZED)")
        logger.info("=" * 80)
        logger.info(f"Input file: {args.input}")
        logger.info(f"Model: {rag_config.embedding.model_name}")
        logger.info(f"Target chunk size: {rag_config.chunking.target_chunk_size} tokens")
        logger.info(f"Embedding batch size: {rag_config.embedding.batch_size}")
        logger.info(f"Storage batch size: {qdrant_config.storage_batch_size}")
        logger.info(f"FP16 enabled: {rag_config.embedding.use_fp16 and rag_config.embedding.device == 'cuda'}")
        
        # Read markdown file
        logger.info("\n[1/5] Reading markdown file...")
        content = read_markdown_file(args.input)
        file_size = Path(args.input).stat().st_size
        logger.info(f"  File size: {file_size:,} bytes")
        
        # Get document metadata
        document_id = args.document_id or get_document_id_from_path(args.input)
        logger.info(f"  Document ID: {document_id}")
        
        # Initialize semantic chunker
        logger.info("\n[2/5] Initializing semantic chunker...")
        chunker = SemanticChunker(rag_config)
        
        # Parse and chunk document
        logger.info("\n[3/5] Parsing and chunking document...")
        logger.info("  Stage 1: Parsing markdown (markdown-it-py)")
        logger.info("  Stage 2: Extracting semantic sections")
        logger.info("  Stage 3: Semantic chunking with sentence boundaries")
        logger.info("  Stage 4: Context enhancement and multi-representation")
        
        chunks = chunker.chunk_document(content, document_id)
        
        if not chunks:
            logger.warning("No chunks generated from document")
            print("\n✗ No chunks generated. Document may be empty or invalid.", file=sys.stderr)
            return 1
        
        logger.info(f"  Generated {len(chunks)} semantic chunks")
        
        print_chunk_statistics(chunks)
        
        logger.info("\n[4/5] Generating embeddings with sentence-transformers...")
        embedder = EmbeddingGenerator(rag_config.embedding)
        
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = embedder.generate_embeddings(chunk_texts)
        
        logger.info(f"  Generated {len(embeddings)} embeddings")
        logger.info(f"  Embedding dimension: {embedder.get_embedding_dimension()}")
        
        # Store in Qdrant (async)
        logger.info("\n[5/5] Storing in Qdrant (async with gRPC)...")
        storage = QdrantStorage(qdrant_config, embedder.get_embedding_dimension())
        
        # Initialize storage (create collection if needed)
        await storage.initialize()
        
        await storage.store_chunks(
            chunks=chunks,
            embeddings=embeddings,
            document_id=document_id
        )
        
        logger.info("  Successfully stored in vector database")

        print("\n" + "=" * 80)
        print("✓ Pipeline completed successfully!")
        print("=" * 80)
        print(f"  Collection: {qdrant_config.collection_name}")
        print(f"  Document ID: {document_id}")
        print(f"  Chunks stored: {len(chunks)}")
        print(f"  Vector dimension: {embedder.get_embedding_dimension()}")
        print(f"  Optimizations: sentence-transformers, gRPC, batch_size={qdrant_config.storage_batch_size}")
        print("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        print("\n✗ Process interrupted by user", file=sys.stderr)
        return 130
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"\n✗ Error: File not found - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point"""
    args = parse_args()
    
    # Run async main
    return asyncio.run(async_main(args))


if __name__ == '__main__':
    sys.exit(main())