from typing import List, Dict, Any


class ChunkStatistics:
    """Calculate and display chunk statistics"""
    
    @staticmethod
    def print_statistics(chunks: List[Any]) -> None:
        """
        Print statistics about generated chunks
        
        Args:
            chunks: List of SemanticChunk objects
        """
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


class SearchResultsDisplay:
    """Display search results in formatted way"""
    
    @staticmethod
    def display_results(
        query: str, 
        results: List[Dict[str, Any]], 
        show_metadata: bool = True
    ) -> None:
        """
        Display search results in a formatted way
        
        Args:
            query: Original query text
            results: List of search results
            show_metadata: Whether to show metadata
        """
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
                if metadata.get('heading'):
                    print(f"Heading: {metadata['heading']}")
                
                if metadata.get('section_path'):
                    print(f"Section: {metadata['section_path']}")
            
            print(f"\nContent:\n{content}")
            print(f"{'-'*80}\n")


class VectorizeOutputFormatter:
    """Format output messages for vectorize command"""
    
    @staticmethod
    def print_pipeline_start(input_file: str, model_name: str, config: Dict[str, Any]) -> None:
        """Print pipeline start banner"""
        print("=" * 80)
        print("Starting RAG-optimized markdown vectorization pipeline (OPTIMIZED)")
        print("=" * 80)
        print(f"Input file: {input_file}")
        print(f"Model: {model_name}")
        print(f"Embedding batch size: {config.get('embedding_batch_size', 'N/A')}")
        print(f"Storage batch size: {config.get('storage_batch_size', 'N/A')}")
        print(f"FP16 enabled: {config.get('fp16_enabled', False)}")
    
    @staticmethod
    def print_file_info(file_size: int, document_id: str) -> None:
        """Print file information"""
        print(f"  File size: {file_size:,} bytes")
        print(f"  Document ID: {document_id}")
    
    @staticmethod
    def print_completion(
        collection_name: str, 
        document_id: str, 
        chunks_count: int, 
        vector_dim: int,
        storage_batch_size: int
    ) -> None:
        """Print completion message"""
        print("\n" + "=" * 80)
        print("✓ Pipeline completed successfully!")
        print("=" * 80)
        print(f"  Collection: {collection_name}")
        print(f"  Document ID: {document_id}")
        print(f"  Chunks stored: {chunks_count}")
        print(f"  Vector dimension: {vector_dim}")
        print(f"  Optimizations: sentence-transformers, gRPC, batch_size={storage_batch_size}")
        print("=" * 80)