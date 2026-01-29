# Bwired - Agentic Coding Guidelines

This file contains essential information for AI agents working on this codebase.

## Build and Run Commands

### Environment Setup
```bash
# Required environment variable (set in server.py)
export KMP_DUPLICATE_LIB_OK="TRUE"  # For NumPy compatibility

# Generate secrets for services
make sec  # Generate secret key for SearXNG
```

### Development Commands
```bash
make i            # Install dependencies: pip install -r requirements.txt
make req          # Generate requirements.txt from imports
make up           # Start services via docker compose: docker compose up -d
make b            # Build and start services: docker compose up --build -d
make r            # Run development server: uvicorn internal.server:app --host 0.0.0.0 --port 8000
make sec          # Generate secret: openssl rand -hex 32
```

### Testing
Currently uses standalone test scripts. To add proper testing:
1. Install pytest: `pip install pytest pytest-asyncio`
2. Create `pytest.ini` for configuration
3. Run tests: `pytest` (all tests) or `pytest path/to/test_file.py::test_function` (single test)

**Existing test pattern**: See `test_searxng_bangs.py` for example test structure using basic assertions and logging.

### Linting and Formatting
No linting tools are currently configured. Recommended additions:
- Black for formatting: `black .`
- Ruff for linting: `ruff check .`
- mypy for type checking: `mypy .`

### Development Workflow
```bash
# Start fresh development environment
make i                    # Install dependencies
make up                   # Start Docker services (Qdrant, SearXNG)
make r                    # Start development server

# For production builds
make b                    # Build and start all services
```

## Code Style Guidelines

### Imports
Order imports in three groups, each separated by a blank line:
1. Standard library: `import logging`, `from typing import List`
2. Third-party: `import numpy`, `from fastapi import FastAPI`
3. Local/internal: `from internal.config import load_config`

### Type Hints
- Use `typing` module types: `List`, `Dict`, `Optional`, `Any`
- Explicit `Optional[T]` not `T | None`
- Dataclasses for configuration: `@dataclass class Config:`
- Type hint all function arguments and return values

### Naming Conventions
- Classes: `PascalCase` (e.g., `DenseEmbedder`, `MarkdownDocumentChunker`)
- Functions/Methods: `snake_case` (e.g., `chunk_document`, `encode`)
- Variables: `snake_case` (e.g., `query_text`, `buffer_elements`)
- Private members: prefix with `_` (e.g., `_chunk_section`, `_is_metadata_noise`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `KMP_DUPLICATE_LIB_OK`)

### Error Handling
- Use try-except with specific exception types
- Log errors with `logger.error()` in except blocks
- Raise `ValueError` for configuration validation errors
- Validate state in `__post_init__` methods of dataclasses

### Logging
- Always create module-level logger: `logger = logging.getLogger(__name__)`
- Use structured logging with context
- Log levels: `logger.info()` for normal operations, `logger.warning()` for issues, `logger.error()` for failures
- Log component initialization with confirmation messages

### Docstrings
- Use triple-quoted docstrings for all classes and public methods
- Multi-line format for complex functions
- Include Args, Returns, and Note sections where applicable
- Keep docstrings focused on behavior, not implementation

### File Organization
- `/internal/` - Main application code
- `/internal/chunkers/` - Document chunking logic
- `/internal/embedding/` - Dense and sparse embedders
- `/internal/processing/` - Text processing and reranking
- `/internal/server/` - FastAPI application
- `/internal/storage/` - Qdrant client
- `/internal/retriever/` - Search and retrieval logic
- `config.yaml` - Configuration file
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Qdrant and SearXNG services
- `searxng/` - SearXNG configuration directory

### Common Patterns
- **Dataclasses with validation**: Use `@dataclass` with `__post_init__` for config validation
- **Abstract base classes**: Use `ABC` with `@abstractmethod` for interfaces (see `BaseDocumentChunker`)
- **Factory pattern**: Component creation via factories (`ChunkerFactory.create()`)
- **Template Method**: Base classes define workflow, subclasses implement specifics
- **Async context managers**: Use `@asynccontextmanager` for FastAPI lifespan events
- **Dependency injection**: Pass dependencies via constructors for testability

### Architecture Patterns
- Abstract base classes with `@abstractmethod` for interfaces
- Factory pattern for component creation (`ChunkerFactory.create()`)
- Dependency injection for testing and flexibility
- Async context managers for lifecycle management (FastAPI lifespan)
- Dataclasses for configuration and structured data

### Important Notes
- Set `KMP_DUPLICATE_LIB_OK` environment variable for NumPy compatibility
- Use `SentenceTransformer` models via the `sentence-transformers` library
- GPU acceleration supported via `device="cuda"` in config
- Spacy model required: `python -m spacy download en_core_web_sm`
- All configuration loaded from `config.yaml` via `load_config()`

### Docker Services
- **Qdrant**: Vector database (ports 6333/6334) for similarity search
- **SearXNG**: Web search engine (port 8888) for external search integration
- Both services started via `make up` or `make b`

### Performance Considerations
- **GPU Support**: Set `device: "cuda"` in config for CUDA acceleration
- **FP16 Precision**: Enable `use_fp16: true` to reduce memory usage on GPU
- **Batch Processing**: Configure `batch_size` for efficient embedding generation
- **Model Caching**: Models are loaded once and reused across requests
