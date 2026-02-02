# Bwired - Agentic Coding Guidelines

## Build/Run/Test Commands

```bash
# Environment setup
export KMP_DUPLICATE_LIB_OK="TRUE"  # Required for NumPy compatibility

# Development
make i            # Install dependencies
make up           # Start Docker services (Qdrant, SearXNG)
make r            # Run server: uvicorn internal.server:app --host 0.0.0.0 --port 8000
make b            # Build and start services
make sec          # Generate SearXNG secret (first time only)

# Testing (when tests exist)
pytest                            # Run all tests
pytest tests/test_file.py         # Run single test file
pytest tests/test_file.py::test_func  # Run single test
pytest --cov=internal --cov-report=html  # With coverage
```

**Services**: Qdrant (6333/6334), SearXNG (8888) | **Verify**: `docker ps`

**Prerequisites**: `python -m spacy download en_core_web_sm`

## Code Style Guidelines

### Imports
Order in three groups, separated by blank lines:
1. Standard library: `import logging`, `from typing import List, Dict, Optional`
2. Third-party: `import numpy`, `from fastapi import FastAPI`
3. Local/internal: `from internal.config import load_config`

### Type Hints
- Use `typing` module: `List`, `Dict`, `Optional`, `Any`, `Literal`
- Use `Optional[T]` not `T | None`
- Type hint all function arguments and return values
- Use `Literal` for restricted strings (e.g., `ChunkerFormat = Literal['markdown']`)

### Naming Conventions
- Classes: `PascalCase` (e.g., `DenseEmbedder`, `MarkdownDocumentChunker`)
- Functions/Methods: `snake_case` (e.g., `chunk_document`, `encode`)
- Variables: `snake_case` (e.g., `query_text`, `buffer_elements`)
- Private members: prefix with `_` (e.g., `_chunk_section`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `KMP_DUPLICATE_LIB_OK`)

### Error Handling & Logging
- Use try-except with specific exception types
- Log errors with `logger.error()` in except blocks
- Raise `ValueError` for configuration validation errors
- Validate state in `__post_init__` methods of dataclasses
- Always create module-level logger: `logger = logging.getLogger(__name__)`

### Docstrings
- Triple-quoted docstrings for all classes and public methods
- Include Args, Returns sections where applicable
- Focus on behavior, not implementation details

## Architecture Patterns

| Pattern | Implementation |
|---------|---------------|
| **Abstract Base Class** | `ABC` with `@abstractmethod` for interfaces (see `BaseDocumentChunker`) |
| **Factory** | Component creation via factories (`ChunkerFactory.create()`) |
| **Dataclass Validation** | `@dataclass` with `__post_init__` for config validation |
| **Template Method** | Base classes define workflow, subclasses implement specifics |
| **Async Context Managers** | `@asynccontextmanager` for FastAPI lifespan events |
| **Dependency Injection** | Pass dependencies via constructors for testability |

## File Organization

| Directory | Purpose |
|-----------|---------|
| `internal/` | Main application code |
| `internal/chunkers/` | Document chunking logic |
| `internal/embedding/` | Dense and sparse embedders |
| `internal/processing/` | Text processing and reranking |
| `internal/server/` | FastAPI application |
| `internal/storage/` | Qdrant client |
| `internal/retriever/` | Search and retrieval logic |
| `internal/api/` | API route handlers |
| `internal/searxng/` | Web search client |

**Key Files**: `config.yaml` (configuration), `requirements.txt`, `docker-compose.yml`

## Important Notes

- **NumPy**: Set `KMP_DUPLICATE_LIB_OK` environment variable
- **Models**: Use `SentenceTransformer` via `sentence-transformers` library
- **GPU**: Set `device: "cuda"` in config for CUDA acceleration
- **Config**: All changes require server restart due to model loading
- **Spacy**: Required model `en_core_web_sm` must be downloaded

## Performance Considerations

- **FP16 Precision**: Enable `use_fp16: true` for GPU memory savings
- **Batch Processing**: Configure `batch_size` for efficient embedding generation
- **Model Caching**: Models loaded once and reused across requests
- **Development**: Use small documents to reduce processing time

## Docker Services

- **Qdrant**: Vector database on ports 6333/6334
- **SearXNG**: Web search on port 8888
- Start with: `make up` or `make b`
