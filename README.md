# Bwired

## Modules

### Research Engine (`internal/research`)
- **Search Orchestrator**: Manages web searches via SearXNG, handling query generation and result aggregation
- **Web Crawler**: Asynchronously crawls websites and processes PDFs using Crawl4AI, converting content to Markdown
- **Fact Extractor**: Uses LLMs (Instructor) to extract structured data from content based on defined templates
- **Template Manager**: Handles CRUD operations for research templates and schemas
- **Pipeline**: Orchestrates the full deep research workflow (Search -> Crawl -> Chunk -> Store -> Extract)

### Data Processing (`internal/processing` & `internal/chunkers`)
- **Markdown Chunker**: Intelligent splitting of content preserving tables, lists, and code blocks
- **Context Compressor**: Reduces retrieved context size using LLMLingua-2 to fit LLM windows
- **Reranker**: Re-orders search results using BAAI/bge-reranker-v2-m3 for higher relevance
- **URL Processor**: Normalizes URLs, calculates relevance scores, and handles deduplication

### Storage & Retrieval (`internal/storage` & `internal/embedding`)
- **Qdrant Client**: Vector database wrapper managing dense and sparse collections
- **Postgres Client**: Relational storage for research sessions, raw documents, and extracted facts
- **Hybrid Embedder**: Combines Dense (BGE-Base) and Sparse (SPLADE) embeddings for robust retrieval

### Infrastructure (`internal/server` & `internal/llm`)
- **FastAPI Server**: REST API providing endpoints for starting and monitoring research
- **LLM Factory**: Unified interface for different LLM providers (OpenAI, Ollama)
- **Token Counter**: Universal token counting and text truncation utilities
- **Config**: Type-safe configuration management using Pydantic models

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