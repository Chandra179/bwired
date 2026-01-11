# Deep Research Agent System

A Python-based agentic AI research system with dynamic templating, recursive discovery, multi-format synthesis, and advanced document chunking.

## Tech Stack

### Core
- **Python 3.10+** with asyncio
- **FastAPI** - REST API server with uvicorn
- **SQLAlchemy 2.0+** - Async ORM with PostgreSQL
- **PostgreSQL + pgvector** - Relational DB with vector similarity
- **Redis** - Priority queue for task scheduling
- **Qdrant** - Vector store (dense + sparse embeddings)

### ML/AI
- **PyTorch** - Deep learning backend
- **Sentence Transformers** - Dense embeddings (BAAI/bge-base-en-v1.5)
- **SPLADE** - Sparse embeddings
- **Instructor** - Structured LLM extraction
- **Crawl4AI** - Web scraping
- **pydantic-ai** - Agentic AI framework

### Document Processing
- **Docling** - PDF to Markdown conversion
- **markdown-it-py** - Markdown AST parsing
- **spaCy** - NLP for text splitting
- **LLMLingua** - Context compression

## Directory Structure

```
bwired/
├── internal/
│   ├── server/              # FastAPI application
│   ├── research/            # Deep research agent pipeline
│   │   ├── nodes/           # Pipeline nodes (initiation, scout, process, discovery, synthesis)
│   │   ├── schema_factory.py # Dynamic Pydantic models
│   │   ├── lead_extractor.py # Citation/concept extraction
│   │   └── pipeline.py      # Main orchestration
│   ├── database/            # PostgreSQL models & client
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── client.py        # Async DB client
│   │   └── qdrant_client.py # Vector store client
│   ├── queue/               # Redis task queue
│   ├── search/              # Web search & scraping
│   ├── chunkers/            # Document chunking system
│   │   ├── markdown/        # Markdown-specific strategies
│   │   ├── base_chunker.py
│   │   └── chunker_factory.py
│   ├── embedding/           # Dense/sparse embeddings & reranker
│   ├── processing/          # PDF extraction, compression
│   ├── config.py            # Configuration dataclasses
│   └── logger.py            # Logging setup
├── config.yaml              # Main configuration
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Infrastructure (PostgreSQL, Redis, SearXNG)
└── Makefile                 # Build/run commands
```

## Code Standards

### Configuration
- Use `dataclasses` for all configuration classes
- Define validation in `__post_init__` methods
- Load from YAML via `load_config()` in `internal/config.py`
- All config is in `config.yaml` at project root

### Database
- Use SQLAlchemy 2.0+ async patterns
- Models inherit from `Base = declarative_base()`
- Use UUID strings for primary keys: `default=lambda: str(uuid.uuid4())`
- Column types: `String`, `Integer`, `Float`, `DateTime`, `JSONB`, `Vector(1536)`
- Define indexes in `__table_args__` tuples
- JSONB for flexible schemas (e.g., `extracted_facts`, `schema_json`)

### Logging
- Use standard Python logging: `logger = logging.getLogger(__name__)`
- Log levels: INFO for normal operations, WARNING for non-critical failures, ERROR for critical
- Import from `internal.logger` for setup: `setup_logging("INFO")`

### Chunking Architecture
1. Parse Markdown into AST (markdown-it-py)
2. Build section hierarchy - group elements under parent headers
3. Apply element-specific chunking strategies:
   - Tables: split by rows, preserve headers
   - Code blocks: split by logical units
   - Lists: split by item groups
   - Text: split by tokens/paragraphs

### Research Pipeline Nodes
All nodes follow consistent patterns:
- **Initiation**: Generate seed questions from goal + template
- **Scout**: Search SearXNG for relevant URLs
- **Process**: Crawl URL → chunk → embed → extract facts (Instructor)
- **Discovery**: Identify leads (citations, concepts) → score links → generate sub-questions
- **Synthesis**: Aggregate facts → generate reports (table/graph/text/PDF)

### Type Hints
- Use `Optional[T]` for nullable values
- Use `List[T]`, `Dict[K, V]` from `typing`
- Return types on all functions
- Pydantic models for structured data (dynamic models via `schema_factory.py`)

### File Naming
- `snake_case` for all Python files
- `models.py` for SQLAlchemy models
- `client.py` for external service clients
- `factory.py` for object creation patterns
- `__init__.py` for package exports

## Development Commands

```bash
# Start infrastructure (PostgreSQL, Redis, SearXNG)
make up

# Install dependencies
make i

# Run FastAPI server
make r

# Server runs on http://0.0.0.0:8000
# API docs: http://localhost:8000/docs
```

## Key Conventions

### Error Handling
- Raise `ValueError` for configuration/validation errors
- Use try/except for initialization failures
- Log errors before raising
- Graceful degradation for optional components (e.g., context compressor)

### Async Patterns
- Use `async def` for DB operations
- Use `asynccontextmanager` for lifespan events
- SQLAlchemy sessions via async engine
- Redis operations via `aioredis`

### Database Migrations
- Use Alembic for schema changes
- Check `internal/database/migrations/`
- Run migrations: `alembic upgrade head`

### Testing
- Test files in `test/` directory
- Use `.http` files for API endpoint testing
- Keep tests focused on single components

### Vector Operations
- Dense embeddings: SentenceTransformer (768-dim)
- Sparse embeddings: SPLADE (high-dim, sparse)
- Reranker: BAAI/bge-reranker-v2-m3 (cross-encoder)
- Storage: Qdrant with HNSW index

## LLM Integration

- Use `pydantic-ai` Agent framework
- Local LLM via Ollama (llama3.2)
- Structured extraction via Instructor (JSON schemas)
- Web scraping via Crawl4AI
- Search via SearXNG multi-engine

## Important Notes

- Run `spacy` download after pip install: `python -m spacy download en_core_web_sm`
- PostgreSQL requires pgvector extension (configured in docker-compose)
- SearXNG for multi-engine search (configured in searxng/settings.yml)
- CUDA available for GPU acceleration (configurable in `config.yaml`)
