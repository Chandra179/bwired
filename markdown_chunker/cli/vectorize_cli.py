import argparse
import sys
import logging
import asyncio
from pathlib import Path

from .config_loader import ConfigurationLoader
from .display import ChunkStatistics, VectorizeOutputFormatter

from ..core.semantic_chunker import SemanticChunker
from ..embedding.embedder import EmbeddingGenerator
from ..storage.qdrant_storage import QdrantStorage
from ..logger import setup_logging

logger = logging.getLogger(__name__)


class VectorizeCommand:
    """Encapsulates vectorize command logic"""
    
    def __init__(self, args):
        self.args = args
        self.config_loader = ConfigurationLoader()
        self.output_formatter = VectorizeOutputFormatter()
        self.stats_printer = ChunkStatistics()
    
    async def execute(self) -> int:
        """
        Execute the vectorize command
        
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            rag_config, qdrant_config, log_level = self.config_loader.load_vectorize_config(
                self.args.config
            )
            
            setup_logging(log_level)
            self._print_start_info(rag_config, qdrant_config)
            
            logger.info("\n[1/5] Reading markdown file...")
            content = read_markdown_file(self.args.input)
            file_size = Path(self.args.input).stat().st_size
            
            # Get document metadata
            document_id = self.args.document_id or Path(self.args.input).stem
            self.output_formatter.print_file_info(file_size, document_id)
            
            # Initialize semantic chunker
            logger.info("\n[2/5] Initializing semantic chunker...")
            chunker = SemanticChunker(rag_config)
            
            # Parse and chunk document
            logger.info("\n[3/5] Parsing and chunking document...")
            self._print_chunking_stages()
            
            chunks = chunker.chunk_document(content, document_id)
            
            if not chunks:
                logger.warning("No chunks generated from document")
                print("\n✗ No chunks generated. Document may be empty or invalid.", file=sys.stderr)
                return 1
            
            logger.info(f"  Generated {len(chunks)} semantic chunks")
            self.stats_printer.print_statistics(chunks)
            
            # Generate embeddings
            logger.info("\n[4/5] Generating embeddings with sentence-transformers...")
            embedder = EmbeddingGenerator(rag_config.embedding)
            
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = embedder.generate_embeddings(chunk_texts)
            
            logger.info(f"  Generated {len(embeddings)} embeddings")
            logger.info(f"  Embedding dimension: {embedder.get_embedding_dimension()}")
            
            # Store in Qdrant
            logger.info("\n[5/5] Storing in Qdrant (async with gRPC)...")
            storage = QdrantStorage(qdrant_config, embedder.get_embedding_dimension())
            
            await storage.initialize()
            await storage.store_chunks(
                chunks=chunks,
                embeddings=embeddings,
                document_id=document_id
            )
            
            logger.info("  Successfully stored in vector database")
            
            # Print completion message
            self.output_formatter.print_completion(
                qdrant_config.collection_name,
                document_id,
                len(chunks),
                embedder.get_embedding_dimension(),
                qdrant_config.storage_batch_size
            )
            
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
    
    def _print_start_info(self, rag_config, qdrant_config):
        """Print startup information"""
        config_info = {
            'embedding_batch_size': rag_config.embedding.batch_size,
            'storage_batch_size': qdrant_config.storage_batch_size,
            'fp16_enabled': rag_config.embedding.use_fp16 and rag_config.embedding.device == 'cuda'
        }
        self.output_formatter.print_pipeline_start(
            self.args.input,
            rag_config.embedding.model_name,
            config_info
        )
    
    def _print_chunking_stages(self):
        """Print chunking stage information"""
        logger.info("  Stage 1: Parsing markdown (markdown-it-py)")
        logger.info("  Stage 2: Extracting semantic sections")
        logger.info("  Stage 3: Semantic chunking with sentence boundaries")
        logger.info("  Stage 4: Context enhancement and multi-representation")


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


def read_markdown_file(file_path: str) -> str:
    """
    Read markdown file content
    
    Args:
        file_path: Path to markdown file
        
    Returns:
        File content as string
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.suffix.lower() in ['.md', '.markdown']:
        raise ValueError(f"Not a markdown file: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return content

def main():
    """Main entry point"""
    args = parse_args()
    command = VectorizeCommand(args)
    return asyncio.run(command.execute())


if __name__ == '__main__':
    sys.exit(main())