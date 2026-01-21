# Bwired - Agentic Coding Guidelines

This file contains essential information for AI agents working on this codebase.

## Build and Run Commands

### Development Commands
```bash
make i            # Install dependencies: pip install -r requirements.txt
make req          # Generate requirements.txt from imports
make up           # Start Qdrant via docker compose: docker compose up -d
make r            # Run development server: uvicorn internal.server:app --host 0.0.0.0 --port 8000
```

### Testing
No test framework is currently configured. To add testing:
1. Install pytest: `pip install pytest pytest-asyncio`
2. Create `pytest.ini` for configuration
3. Run tests: `pytest` (all tests) or `pytest path/to/test_file.py::test_function` (single test)

### Linting and Formatting
No linting tools are currently configured. Recommended additions:
- Black for formatting: `black .`
- Ruff for linting: `ruff check .`
- mypy for type checking: `mypy .`

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
- `config.yaml` - Configuration file
- `requirements.txt` - Python dependencies

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
