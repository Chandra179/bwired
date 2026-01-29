# Bwired

A production-ready RAG (Retrieval-Augmented Generation) system that combines advanced document processing, hybrid search, and web search capabilities.

## Features

- **Document Processing**: Convert PDFs and other formats to Markdown using Docling
- **Intelligent Chunking**: Advanced Markdown-aware chunking with special handling for:
  - Tables, code blocks, and lists
  - Header-based sections with hierarchy preservation
  - Token overlap between chunks for context continuity
- **Hybrid Search**: Combine dense (semantic) and sparse (keyword) embeddings for better retrieval
- **Reranking**: Reorder search results using BAAI/bge-reranker-v2-m3 for improved relevance
- **Context Compression**: Reduce retrieved context size using LLMLingua
- **Web Search Integration**: SearXNG-powered web search with bang syntax support
- **Vector Storage**: Qdrant vector database for efficient similarity search
- **FastAPI**: RESTful API with comprehensive endpoints and CORS support

## Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- CUDA-compatible GPU (optional, for acceleration)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd bwired

# Install dependencies
make i

# Generate SearXNG secret (first time only)
make sec

# Start Docker services (Qdrant + SearXNG)
make up

# Run the development server
make r
```

The server will start on `http://localhost:8000`

## Architecture

### Components

- **Chunker Factory**: Creates appropriate chunkers based on document format
- **Dense Embedder**: Generates dense vectors using BAAI/bge-base-en-v1.5
- **Sparse Embedder**: Generates sparse vectors using SPLADE
- **Reranker**: Reorders search results for better relevance
- **Qdrant Client**: Manages vector storage and retrieval
- **Document Processor**: Handles text splitting and sentence segmentation
- **Web Search Client**: SearXNG integration with bang syntax support
- **Server**: FastAPI application with lifespan management

### Models

- **Dense Embedding**: BAAI/bge-base-en-v1.5 (768 dimensions)
- **Sparse Embedding**: prithivida/Splade_PP_en_v1
- **Reranker**: BAAI/bge-reranker-v2-m3
- **Context Compression**: microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank
- **Document Processing**: Docling (PDF → Markdown conversion)

## Project Structure

```
bwired/
├── internal/
│   ├── api/                    # FastAPI endpoints
│   │   ├── documents.py        # Document upload & PDF extraction
│   │   ├── vector_search.py    # Vector search endpoints
│   │   ├── web_search.py       # Web search endpoints  
│   │   ├── health.py           # Health check endpoints
│   │   └── __init__.py
│   ├── chunkers/              # Document chunking logic
│   │   ├── base_chunker.py
│   │   ├── chunker_factory.py
│   │   ├── schema.py
│   │   └── markdown/           # Markdown-specific chunking
│   │       ├── markdown_chunker.py
│   │       ├── markdown_parser.py
│   │       ├── section_analyzer.py
│   │       ├── overlap_handler.py
│   │       ├── table_splitter.py
│   │       ├── code_splitter.py
│   │       ├── list_splitter.py
│   │       ├── text_splitter.py
│   │       └── utils.py
│   ├── embedding/             # Dense and sparse embedders
│   │   ├── dense_embedder.py   # BAAI/bge-base-en-v1.5
│   │   └── sparse_embedder.py  # SPLADE
│   ├── processing/            # Text processing and reranking
│   │   ├── document_processor.py
│   │   ├── document_extractor.py
│   │   ├── reranker.py         # BAAI/bge-reranker-v2-m3
│   │   ├── context_compressor.py  # LLMLingua
│   │   └── sentence_splitter.py
│   ├── retriever/             # Search and retrieval logic
│   │   ├── retriever.py
│   │   └── metadata.py
│   ├── storage/               # Qdrant client
│   │   └── qdrant_client.py
│   ├── searxng/               # Web search client
│   │   ├── client.py
│   │   ├── models.py
│   │   ├── bangs.py
│   │   └── exceptions.py
│   ├── server/                # FastAPI application
│   │   └── server.py
│   ├── config.py              # Configuration management
│   ├── logger.py              # Logging setup
│   ├── parser.py              # Document parsing
│   └── token_counter.py       # Token counting utilities
├── config.yaml                # Main configuration file
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Qdrant & SearXNG services
├── Makefile                  # Development commands
├── searxng/settings.yml      # SearXNG configuration
├── example.pdf               # Sample PDF for testing
├── example.md                # Sample markdown file
├── api.http                  # API testing file
└── README.md                 # Project documentation
```

## API Endpoints

### Health Checks
- `GET /` - Basic health check
- `GET /health` - Detailed component status

### Document Processing  
- `POST /documents/extract-pdf` - Convert PDF to markdown
- `POST /documents/upload` - Upload and process markdown files

### Search
- `POST /vector-search` - Search documents with hybrid embeddings

### Web Search
- `POST /web-search` - General web search
- `POST /web-search/bang` - Bang syntax search (!go, !yhn, !re)
- `GET /web-search/bangs` - List available bang shortcuts
- `POST /web-search/markdown` - Web search with URL→markdown conversion

## Advanced Chunking Features

The markdown chunker provides intelligent document processing with:

### Special Content Handling
- **Tables**: Preserves table structure and context
- **Code Blocks**: Maintains code formatting and language context
- **Lists**: Preserves list hierarchy and numbering
- **Headers**: Maintains document structure and section hierarchy

### Chunking Strategy
- **Token-based**: 512 tokens per chunk with 50 token overlap
- **Context Preservation**: Overlap ensures continuity between chunks
- **Section Awareness**: Respects document structure and semantic boundaries
- **Smart Splitting**: Avoids breaking sentences or code blocks inappropriately

## Web Search Integration

### SearXNG Integration
- **Private Search**: Privacy-focused web search engine
- **Bang Syntax**: Direct search on specific platforms (!go, !yhn, !re, etc.)
- **Multiple Sources**: Aggregates results from various search engines
- **Customizable**: Configurable search engines and results

### Bang Syntax Examples
- `!go query` - Search Google
- `!yhn query` - Search Yahoo
- `!re query` - Search Reddit
- `!w query` - Search Wikipedia

### Markdown Conversion
- **URL Processing**: Convert web pages to clean markdown
- **Content Extraction**: Extract main content from web pages
- **Structured Output**: Preserve headings, lists, and formatting

## Configuration

### Chunking Settings
```yaml
chunking:
  chunk_size: 512          # Tokens per chunk
  overlap_tokens: 50       # Overlap between chunks
  include_header_path: true # Include section headers in chunk context
```

### Embedding Configuration
```yaml
embedding:
  device: "cuda"           # GPU or CPU
  model_dim: 768          # Dense embedding dimensions
  token_limit: 512        # Maximum tokens for embeddings
  
  dense:
    model_name: "BAAI/bge-base-en-v1.5"
    batch_size: 32
    use_fp16: true        # FP16 precision for GPU memory savings
    
  sparse:
    model_name: "prithivida/Splade_PP_en_v1"
    batch_size: 8
    threads: 4
```

### Search and Reranking
```yaml
reranker:
  model_name: "BAAI/bge-reranker-v2-m3"
  device: "cpu"
  batch_size: 32
  enabled: true
  
compression:
  model_name: "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
  compression_ratio: 0.5  # Target compression ratio
  token_limit: null      # Optional maximum tokens
```

### External Services
```yaml
qdrant:
  url: "http://localhost:6333"
  distance_metric: "Cosine"
  grpc_port: 6334
  storage_batch_size: 500

searxng:
  url: "http://localhost:8888"
  timeout: 30.0
  max_results: 100
  retry_attempts: 3
  retry_delay: 1.0
```

## Development Workflow

### Makefile Commands
```bash
make i            # Install dependencies: pip install -r requirements.txt
make req          # Generate requirements.txt from imports
make up           # Start services via docker compose: docker compose up -d
make b            # Build and start services: docker compose up --build -d
make r            # Run development server: uvicorn internal.server:app --host 0.0.0.0 --port 8000
make sec          # Generate secret: openssl rand -hex 32
```

### Development Setup
```bash
# Start fresh development environment
make i                    # Install dependencies
make sec                  # Generate SearXNG secret (first time)
make up                   # Start Docker services (Qdrant, SearXNG)
make r                    # Start development server

# For production builds
make b                    # Build and start all services

# Verify setup
make r                    # Server should start without errors on port 8000
```

## Performance Considerations

### GPU Acceleration
- **CUDA Support**: Set `device: "cuda"` in config for GPU acceleration
- **FP16 Precision**: Enable `use_fp16: true` to reduce memory usage on GPU
- **Batch Processing**: Configure `batch_size` for efficient embedding generation

### Memory and Performance
- **Model Caching**: Models are loaded once and reused across requests
- **Batch Operations**: Use appropriate batch sizes for your hardware
- **Token Limits**: Configure chunk sizes based on your model limits
- **Vector Storage**: Qdrant provides efficient similarity search at scale

### Environment Variables
```bash
# Required for NumPy compatibility
export KMP_DUPLICATE_LIB_OK="TRUE"
```
