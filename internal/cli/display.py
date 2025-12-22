from typing import List, Dict, Any, Optional
import sys


class SearchResultsDisplay:
    """Handles terminal output formatting for search results"""
    
    def display_results(
        self, 
        query: str, 
        results: List[Dict[str, Any]], 
        compressed_context: Optional[str] = None
    ):
        """
        Display search results and optional compressed context to terminal
        
        Args:
            query: The search query
            results: List of search results with scores and metadata
            compressed_context: Optional compressed version of all results
        """
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")
        
        if not results:
            print("No results found.")
            return
        
        print(f"Found {len(results)} results:\n")
        
        # Display individual results
        for i, result in enumerate(results, 1):
            self._display_result(i, result)
        
        # Display compressed context if available
        if compressed_context:
            self._display_compressed_context(compressed_context)
    
    def _display_result(self, index: int, result: Dict[str, Any]):
        """Display a single search result"""
        score = result.get("score", 0.0)
        content = result.get("content", "")
        metadata = result.get("metadata", {})
        
        print(f"{'─'*80}")
        print(f"Result #{index} | Score: {score:.4f}")
        print(f"{'─'*80}")
        
        # Display metadata
        doc_path = metadata.get("document_path", "N/A")
        section_path = metadata.get("section_path", "N/A")
        chunk_index = metadata.get("chunk_index", "N/A")
        
        print(f"Document: {doc_path}")
        print(f"Section: {section_path}")
        print(f"Chunk: {chunk_index}")
        print()
        
        # Display content (truncated if too long)
        max_display_length = 500
        if len(content) > max_display_length:
            display_content = content[:max_display_length] + "..."
        else:
            display_content = content
        
        print(display_content)
        print()
    
    def _display_compressed_context(self, compressed_context: str):
        """Display compressed context section"""
        print(f"\n{'='*80}")
        print("COMPRESSED CONTEXT")
        print(f"{'='*80}\n")
        
        # Display compressed content
        print(compressed_context)
        print(f"\n{'='*80}\n")


class ChunkStatistics:
    """Handles display of chunking statistics"""
    
    def print_statistics(self, chunks: List[Any]):
        """
        Print statistics about generated chunks
        
        Args:
            chunks: List of document chunks
        """
        if not chunks:
            return
        
        # Calculate statistics
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        total_chars = sum(chunk_sizes)
        avg_size = total_chars / len(chunks) if chunks else 0
        min_size = min(chunk_sizes) if chunk_sizes else 0
        max_size = max(chunk_sizes) if chunk_sizes else 0
        
        print(f"\n  Chunk Statistics:")
        print(f"    Total chunks: {len(chunks)}")
        print(f"    Total characters: {total_chars:,}")
        print(f"    Average chunk size: {avg_size:.0f} chars")
        print(f"    Min chunk size: {min_size} chars")
        print(f"    Max chunk size: {max_size} chars")


class VectorizeOutputFormatter:
    """Handles formatted output for vectorization process"""
    
    def print_pipeline_start(self, input_file: str, model_name: str, config_info: Dict[str, Any]):
        """
        Print pipeline start information
        
        Args:
            input_file: Path to input file
            model_name: Name of embedding model
            config_info: Dictionary with configuration details
        """
        print(f"\n{'='*80}")
        print("VECTORIZATION PIPELINE")
        print(f"{'='*80}")
        print(f"\nInput: {input_file}")
        print(f"Embedding Model: {model_name}")
        print(f"Embedding Batch Size: {config_info.get('embedding_batch_size', 'N/A')}")
        print(f"Storage Batch Size: {config_info.get('storage_batch_size', 'N/A')}")
        
        if config_info.get('fp16_enabled'):
            print(f"FP16 Optimization: Enabled")
        
        print(f"{'='*80}\n")
    
    def print_file_info(self, file_size: int, document_id: str):
        """
        Print file information
        
        Args:
            file_size: Size of file in bytes
            document_id: Document identifier
        """
        size_kb = file_size / 1024
        print(f"  File size: {size_kb:.2f} KB")
        print(f"  Document ID: {document_id}")
    
    def print_completion(
        self, 
        collection_name: str,
        document_id: str,
        num_chunks: int,
        embedding_dim: int,
        batch_size: int
    ):
        """
        Print completion summary
        
        Args:
            collection_name: Name of Qdrant collection
            document_id: Document identifier
            num_chunks: Number of chunks processed
            embedding_dim: Dimension of embeddings
            batch_size: Batch size used for storage
        """
        print(f"\n{'='*80}")
        print("✓ VECTORIZATION COMPLETE")
        print(f"{'='*80}")
        print(f"\nCollection: {collection_name}")
        print(f"Document ID: {document_id}")
        print(f"Chunks Stored: {num_chunks}")
        print(f"Embedding Dimension: {embedding_dim}")
        print(f"Batch Size: {batch_size}")
        print(f"\n{'='*80}\n")