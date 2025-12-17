"""
Example usage of the RAG-optimized semantic chunker
"""
import logging
from markdown_chunker.config import RAGChunkingConfig, ChunkingConfig, ContextConfig, EmbeddingConfig
from markdown_chunker.semantic_chunker import SemanticChunker
from markdown_chunker.embedder import EmbeddingGenerator
from markdown_chunker.storage import QdrantStorage
from markdown_chunker.config import QdrantConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    # Example 1: Basic usage with default configuration
    print("=" * 80)
    print("Example 1: Basic Semantic Chunking")
    print("=" * 80)
    
    # Create configuration
    config = RAGChunkingConfig()
    
    # Initialize chunker
    chunker = SemanticChunker(config)
    
    # Sample markdown content
    markdown_content = """
# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that focuses on building systems that can learn from data.

## Types of Machine Learning

### Supervised Learning

Supervised learning uses labeled data to train models. Common algorithms include:
- Linear Regression
- Decision Trees
- Neural Networks

### Unsupervised Learning

Unsupervised learning finds patterns in unlabeled data.

## Example Code

```python
import numpy as np
from sklearn.linear_model import LinearRegression

# Create sample data
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2, 4, 6, 8, 10])

# Train model
model = LinearRegression()
model.fit(X, y)
```

## Performance Metrics

| Metric | Description | Range |
|--------|-------------|-------|
| Accuracy | Correct predictions / Total | 0-1 |
| Precision | True Positives / (TP + FP) | 0-1 |
| Recall | True Positives / (TP + FN) | 0-1 |
"""
    
    # Chunk the document
    chunks = chunker.chunk_document(
        content=markdown_content,
        document_id="ml_intro",
        document_title="Introduction to Machine Learning"
    )
    
    print(f"\nGenerated {len(chunks)} semantic chunks:\n")
    
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}:")
        print(f"  Type: {chunk.chunk_type}")
        print(f"  Section: {' > '.join(chunk.section_path)}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Content preview: {chunk.original_content[:100]}...")
        
        if chunk.entities:
            print(f"  Entities: {chunk.entities}")
        
        if chunk.has_multi_representation:
            print(f"  Multi-representation: Yes")
            print(f"  Description: {chunk.natural_language_description}")
        
        print()
    
    # Example 2: Custom configuration for larger chunks
    print("=" * 80)
    print("Example 2: Custom Configuration")
    print("=" * 80)
    
    custom_config = RAGChunkingConfig(
        chunking=ChunkingConfig(
            target_chunk_size=500,  # Larger chunks
            min_chunk_size=200,
            keep_tables_intact=True,
            keep_code_blocks_intact=True,
            use_sentence_boundaries=True
        ),
        context=ContextConfig(
            include_surrounding_context=True,
            surrounding_sentences_before=3,
            surrounding_sentences_after=2,
            extract_entities=True,
            create_table_descriptions=True,
            create_code_descriptions=True
        ),
        embedding=EmbeddingConfig(
            model_name="BAAI/bge-base-en-v1.5",
            max_token_limit=512
        )
    )
    
    custom_chunker = SemanticChunker(custom_config)
    custom_chunks = custom_chunker.chunk_document(
        content=markdown_content,
        document_id="ml_intro_custom",
        document_title="Introduction to Machine Learning"
    )
    
    print(f"\nGenerated {len(custom_chunks)} chunks with custom config\n")
    
    # Example 3: Full pipeline with embeddings and storage
    print("=" * 80)
    print("Example 3: Full Pipeline (Chunking + Embedding + Storage)")
    print("=" * 80)
    
    try:
        # Initialize embedding generator
        embedder = EmbeddingGenerator(config.embedding)
        
        # Generate embeddings for chunks
        texts = [chunk.content for chunk in chunks]
        embeddings = embedder.generate_embeddings(texts)
        
        print(f"Generated {len(embeddings)} embeddings")
        print(f"Embedding dimension: {embedder.get_embedding_dimension()}")
        
        # Initialize Qdrant storage
        qdrant_config = QdrantConfig(
            url="http://localhost:6333",
            collection_name="ml_docs"
        )
        
        storage = QdrantStorage(qdrant_config, embedder.get_embedding_dimension())
        
        # Store chunks with embeddings
        storage.store_chunks(
            chunks=chunks,
            embeddings=embeddings,
            document_id="ml_intro",
            document_title="Introduction to Machine Learning"
        )
        
        print("\nSuccessfully stored chunks in Qdrant!")
        
        # Example search
        query = "What are types of machine learning?"
        query_embedding = embedder.generate_embedding(query)
        
        results = storage.search(
            query_embedding=query_embedding,
            limit=3,
            score_threshold=0.5
        )
        
        print(f"\nSearch results for: '{query}'")
        for i, result in enumerate(results):
            print(f"\nResult {i + 1} (score: {result['score']:.3f}):")
            print(f"Content: {result['content'][:200]}...")
            print(f"Section: {result['metadata'].get('section_context', 'N/A')}")
        
    except Exception as e:
        print(f"\nNote: Full pipeline requires running Qdrant instance")
        print(f"Error: {e}")
    
    # Example 4: Analyzing chunk distribution
    print("\n" + "=" * 80)
    print("Example 4: Chunk Analysis")
    print("=" * 80)
    
    chunk_types = {}
    total_tokens = 0
    
    for chunk in chunks:
        chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
        total_tokens += chunk.token_count
    
    print("\nChunk Distribution:")
    for chunk_type, count in sorted(chunk_types.items()):
        print(f"  {chunk_type}: {count}")
    
    print(f"\nTotal tokens: {total_tokens}")
    print(f"Average tokens per chunk: {total_tokens / len(chunks):.1f}")
    
    # Show chunks with multi-representation
    multi_repr_chunks = [c for c in chunks if c.has_multi_representation]
    print(f"\nChunks with multi-representation: {len(multi_repr_chunks)}")
    
    for chunk in multi_repr_chunks:
        print(f"\n  Type: {chunk.chunk_type}")
        print(f"  Description: {chunk.natural_language_description}")


if __name__ == "__main__":
    main()