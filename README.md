# Bwired

## Features

- **Document Processing**: Convert PDFs and other formats to Markdown using Docling
- **Intelligent Chunking**: Advanced Markdown-aware chunking with special handling for:
  - Tables, code blocks, and lists
  - Header-based sections
  - Token overlap between chunks
- **Hybrid Search**: Combine dense and sparse embeddings for better retrieval
- **Reranking**: Reorder search results using BAAI/bge-reranker-v2-m3
- **Context Compression**: Reduce retrieved context size with LLMLingua
- **Vector Storage**: Qdrant vector database for efficient similarity search
- **FastAPI**: RESTful API with CORS support

## Architecture

### Components

- **Chunker Factory**: Creates appropriate chunkers based on document format
- **Dense Embedder**: Generates dense vectors using BAAI/bge-base-en-v1.5
- **Sparse Embedder**: Generates sparse vectors using SPLADE
- **Reranker**: Reorders search results for better relevance
- **Qdrant Client**: Manages vector storage and retrieval
- **Document Processor**: Handles text splitting and sentence segmentation
- **Server**: FastAPI application with lifespan management

### Models

- Dense Embedding: BAAI/bge-base-en-v1.5 (768 dimensions)
- Sparse Embedding: prithivida/Splade_PP_en_v1
- Reranker: BAAI/bge-reranker-v2-m3
- Context Compression: microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank

## Development

### Project Structure

```
bwired/
├── internal/
│   ├── chunkers/              # Document chunking logic
│   │   ├── base_chunker.py
│   │   ├── chunker_factory.py
│   │   └── markdown/
│   │       ├── text_splitter.py
│   │       ├── table_splitter.py
│   │       └── list_splitter.py
│   │
│   ├── embedding/             # Embedding models
│   │   ├── dense_embedder.py
│   │   └── sparse_embedder.py
│   │
│   ├── processing/            # Text processing and reranking
│   │   ├── sentence_splitter.py
│   │   ├── document_extractor.py
│   │   ├── reranker.py
│   │   └── context_compressor.py
│   │
│   ├── storage/               # Data persistence
│   │   ├── qdrant_client.py       # Vector storage
│   │   └── postgres_client.py     # Research data (NEW)
│   │
│   ├── research/                  # Deep research components (NEW)
│   │   ├── template_manager.py    # Template CRUD and selection
│   │   ├── search_orchestrator.py # SearXNG integration
│   │   ├── url_processor.py       # URL deduplication and scoring
│   │   ├── web_crawler.py         # Crawl4AI wrapper
│   │   ├── fact_extractor.py      # Structured extraction
│   │   └── research_pipeline.py   # End-to-end orchestration
│   │
│   ├── server/                # FastAPI application
│   │   ├── server.py
│   │   └── research_api.py    # Research endpoints
│   │
│   ├── config.py              # Configuration management
│   └── logger.py              # Logging setup
│
├── migrations/                # Database migrations
│   └── 001_initial_schema.sql
│
├── templates/                 # Research templates
│   └── economy_history.json
│
├── config.yaml                # Application configuration
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Services (Qdrant, PostgreSQL, SearXNG)
├── Makefile                   # Development commands
├── README.md                  # This file
└── TODO.md                    # Implementation roadmap
```

## API Endpoints
1. Research Endpoints
- POST /research/start - Initiate research with query
- POST /research/templates - Create/update research templates
- GET /research/templates - List available templates