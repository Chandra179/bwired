# Bwired

Search engine and vectorizatiion

![Search](/img/news_search.png)

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
- **UI Search Categories**: Multiple specialized search interfaces for:
  - News - Latest headlines and articles
  - General - Broad web search
  - Science - Academic and research content
  - Books - Literature and publication search
- **Vector Storage**: Qdrant vector database for efficient similarity search
- **FastAPI**: RESTful API with comprehensive endpoints and CORS support

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
├── ui/                         # Frontend UI application (SolidJS + Vite)
│   ├── src/
│   │   ├── components/         # Search UI components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # API service layer
│   │   └── assets/             # Static assets
│   ├── public/                 # Public static files
│   ├── package.json
│   └── vite.config.js
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