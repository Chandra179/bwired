"""
Example script demonstrating programmatic usage of the markdown chunker
"""
import logging
from pathlib import Path

from markdown_chunker import (
    EmbeddingConfig,
    QdrantConfig,
    TokenCounter,
    MarkdownChunker,
    EmbeddingGenerator,
    QdrantStorage
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    
    # ==========================================================================
    # STEP 1: Configure
    # ==========================================================================
    
    logger.info("Setting up configuration...")
    
    # Embedding configuration
    embedding_config = EmbeddingConfig(
        model_name="BAAI/bge-base-en-v1.5",  # Or any HuggingFace model
        max_token_limit=512,
        target_chunk_size=400,
        min_chunk_size=100,
        overlap_tokens=50,
        device="cpu"  # Change to "cuda" if GPU available
    )
    
    # Qdrant configuration
    qdrant_config = QdrantConfig(
        url="http://localhost:6333",  # Local Qdrant
        collection_name="example_docs",
        create_if_not_exists=True
    )
    
    # ==========================================================================
    # STEP 2: Read Markdown File
    # ==========================================================================
    
    logger.info("Reading markdown file...")
    
    markdown_file = "sample_document.md"
    
    if not Path(markdown_file).exists():
        logger.error(f"File not found: {markdown_file}")
        return
    
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    document_id = Path(markdown_file).stem
    document_title = "Sample Financial Report"
    
    logger.info(f"Processing document: {document_title}")
    
    # ==========================================================================
    # STEP 3: Initialize Components
    # ==========================================================================
    
    logger.info("Initializing components...")
    
    # Token counter
    token_counter = TokenCounter(embedding_config.model_name)
    
    # Chunker
    chunker = MarkdownChunker(embedding_config, token_counter)
    
    # Embedder
    embedder = EmbeddingGenerator(embedding_config)
    
    # Storage
    storage = QdrantStorage(
        qdrant_config, 
        embedder.get_embedding_dimension()
    )
    
    # ==========================================================================
    # STEP 4: Parse and Chunk Document
    # ==========================================================================
    
    logger.info("Parsing and chunking document...")
    
    chunks = chunker.chunk_document(content, document_id, document_title)
    
    logger.info(f"Generated {len(chunks)} chunks")
    
    # Print some statistics
    total_tokens = sum(chunk.token_count for chunk in chunks)
    avg_tokens = total_tokens // len(chunks) if chunks else 0
    
    print("\n" + "="*60)
    print("CHUNKING RESULTS")
    print("="*60)
    print(f"Total chunks:        {len(chunks)}")
    print(f"Total tokens:        {total_tokens:,}")
    print(f"Average tokens:      {avg_tokens}")
    print(f"Min tokens:          {min(c.token_count for c in chunks)}")
    print(f"Max tokens:          {max(c.token_count for c in chunks)}")
    print("="*60 + "\n")
    
    # Show first few chunks
    print("First 3 chunks:")
    print("-" * 60)
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i+1}:")
        print(f"  Type: {chunk.chunk_type}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Content preview: {chunk.content[:100]}...")
        print(f"  Header path: {' > '.join(chunk.metadata.get('header_path', []))}")
    print("-" * 60)
    
    # ==========================================================================
    # STEP 5: Generate Embeddings
    # ==========================================================================
    
    logger.info("Generating embeddings...")
    
    chunk_texts = [chunk.content for chunk in chunks]
    embeddings = embedder.generate_embeddings(chunk_texts, batch_size=16)
    
    logger.info(f"Generated {len(embeddings)} embeddings")
    
    # ==========================================================================
    # STEP 6: Store in Qdrant
    # ==========================================================================
    
    logger.info("Storing chunks in Qdrant...")
    
    storage.store_chunks(
        chunks=chunks,
        embeddings=embeddings,
        document_id=document_id,
        document_title=document_title,
        batch_size=50
    )
    
    logger.info("Storage complete!")
    
    # ==========================================================================
    # STEP 7: Verify Storage
    # ==========================================================================
    
    logger.info("Verifying storage...")
    
    collection_info = storage.get_collection_info()
    
    print("\n" + "="*60)
    print("QDRANT COLLECTION INFO")
    print("="*60)
    print(f"Collection:          {collection_info['name']}")
    print(f"Vector count:        {collection_info['vectors_count']}")
    print(f"Vector dimension:    {collection_info['vector_size']}")
    print(f"Distance metric:     {collection_info['distance']}")
    print("="*60 + "\n")
    
    # ==========================================================================
    # STEP 8: Example Search (Optional)
    # ==========================================================================
    
    logger.info("Performing example search...")
    
    # Search for content related to "revenue"
    query_text = "What was the revenue performance?"
    query_embedding = embedder.generate_embedding(query_text)
    
    search_results = storage.search(
        query_embedding=query_embedding,
        limit=3
    )
    
    print("\n" + "="*60)
    print(f"SEARCH RESULTS for: '{query_text}'")
    print("="*60)
    for i, result in enumerate(search_results, 1):
        print(f"\nResult {i}:")
        print(f"  Score: {result['score']:.4f}")
        print(f"  Type: {result['metadata']['chunk_type']}")
        print(f"  Header: {result['metadata'].get('header_path_str', 'N/A')}")
        print(f"  Content preview: {result['content'][:150]}...")
    print("="*60 + "\n")
    
    logger.info("Example completed successfully!")
    
    print("\n✓ Success! Your document has been chunked and stored.")
    print(f"✓ Collection '{qdrant_config.collection_name}' contains {len(chunks)} chunks")
    print(f"✓ You can now query this collection using Qdrant's API")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)