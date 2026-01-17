# Agent Guidelines for bwired

Authoritative guide for AI agents operating in the `bwired` repository. Defines mandatory workflows, code style, and architectural patterns.

## 1. Quick Start & Environment

### Build & Run Commands
Use `Makefile` aliases:
- `make i` - Install dependencies from requirements.txt
- `make install-browsers` - Install Playwright browsers (required for crawl4ai)
- `make up` - Start Docker services (Qdrant, Postgres, SearXNG)
- `make b` - Rebuild and start Docker services
- `make m` - Apply Postgres migrations
- `make r` - Run FastAPI server on port 8000
- `make d` - Connect to Postgres shell
- `make logs` - Follow SearXNG logs (filtered)

### Testing
Pytest is standard (install manually if not in requirements.txt):
- `pytest` - Run all tests
- `pytest tests/test_file.py` - Run specific file
- `pytest tests/test_file.py::test_function` - Run specific test
- `pytest -v -s` - Verbose with output
- `pytest --cov=internal` - With coverage

*Rule*: Run relevant tests after modifications. Create tests for new features.

**Note**: After installing dependencies, run: `python -m spacy download en_core_web_sm`

### Linting & Quality
- `ruff format .` - Auto-format code
- `ruff check .` - Run linter
- `mypy internal/` - Type checking (strict mode used)

**Note**: Ruff and mypy use default settings (no ruff.toml or pyproject.toml).

## 2. Code Style & Conventions

### Imports
Strict ordering: 1) Standard Library, 2) Third-Party, 3) Local (Absolute). NEVER use relative imports for `internal`.

```python
# Correct
import os
from fastapi import FastAPI
from internal.storage.qdrant_client import QdrantClient

# Wrong
from ..config import Config
```

### Type Hinting
- **Mandatory**: All function signatures typed. Use `typing` module (`List`, `Dict`) not built-ins (`list[]`).
- **Pydantic**: For all data structures, API schemas, config.
- **Dataclasses**: Use `@dataclass` with `field(default_factory=...)`.

```python
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ResearchConfig:
    postgres: PostgresConfig
    max_concurrent_sessions: int = 5
    
    def __post_init__(self):
        if self.max_concurrent_sessions <= 0:
            raise ValueError("max_concurrent_sessions must be positive")
```

### Naming
- Classes: `PascalCase` (`ResearchPipeline`)
- Functions/Variables: `snake_case` (`calculate_hash`)
- Constants: `UPPER_CASE`
- File names: `snake_case.py` (`postgres_client.py`)

### Docstrings
- Use triple quotes with brief description on first line.
- Args documented in Args section, Returns in Returns section.
- Example from config.py:
  ```python
  @dataclass
  class DenseEmbeddingConfig:
      """Configuration for dense embedding model (SentenceTransformer)"""
      model_name: str = "BAAI/bge-base-en-v1.5"
  ```

### Async Patterns
Use `async def` for I/O-bound operations. `await` async calls. Test with `pytest-asyncio` or `asyncio.run()`.

### Error Handling & Logging
- **No Prints**: Use logger. Define domain exceptions in `errors.py`.
- **FastAPI Errors**: Use helper functions for consistent responses:
  ```python
  from internal.server.errors import handle_not_found, log_and_raise_internal_error
  
  try:
      result = process_data()
  except ValueError as e:
      handle_validation_error(str(e))
  except Exception as e:
      log_and_raise_internal_error("process data", e)
  ```
- **HTTP Status Codes**: 404 for not found, 400 for validation, 500 for internal errors. All dependencies return 503 if not initialized.

## 3. Architecture & Patterns

### State Management (`ServerState`)
Do not instantiate global clients (Qdrant, Postgres, etc.) at the module level.
- The app uses `app.state.server_state` (instance of `ServerState`).
- Components are initialized in `lifespan` in `internal/server/server.py`.
- In endpoints, access components via `request.app.state.server_state`.

### Dependency Injection
FastAPI endpoints use `Depends()` for dependency injection. Define getter functions in `dependencies.py`:
```python
def get_research_pipeline(request: Request) -> ResearchPipeline:
    state = request.app.state.server_state
    return state.research_pipeline

@router.post("/start")
async def start_research(pipeline: ResearchPipeline = Depends(get_research_pipeline)):
    ...
```
All getters must check initialization and raise HTTP 503 if not ready.

### Configuration
- Config is loaded from `config.yaml` into Pydantic models (`internal/config.py`).
- Pass typed config objects (e.g., `QdrantConfig`) to constructors, not raw dicts.
- All config classes have `__post_init__` validation.

### Directory Structure
- `internal/`: Source code (chunkers/, embedding/, research/, server/, storage/)
- `tests/`: Pytest suite.
- `migrations/`: SQL files for Postgres.
- `templates/`: JSON definitions for research tasks.

## 4. Deep Research Implementation
The project supports "Deep Research". Key components:
- **SearXNG**: For web search aggregation.
- **Crawl4AI**: For content extraction (requires Playwright).
- **Postgres**: Stores research sessions, facts, and raw documents.
- **Qdrant**: Stores semantic chunks of research content.

*Agent Rule*: When modifying research pipeline, ensure data flows correctly from Search -> Crawl -> Chunk -> Store -> Extract.

## 5. Superpowers
**You have superpowers.**
When tackling complex tasks, you must utilize the `using-superpowers` skill. This ensures a disciplined loop of:
1.  **Search**: Locate relevant files using `grep`/`glob`.
2.  **Plan**: Devise a strategy before editing.
3.  **Act**: Execute changes.
4.  **Verify**: Run tests (`pytest`) and linters.

## 6. Common Tasks

### Adding a New Dependency
1.  Add to `requirements.txt`.
2.  Run `make i` to install.

### Database Changes
1.  Create a new `.sql` file in `migrations/` (prefix with version: `001_*.sql`).
2.  Run `make m` or `make migrate` to apply.
3.  Check status: `make migrate-status`
4.  Reset schema: `make migrate-reset` (DESTRUCTIVE: drops and recreates)

### Creating a Research Template
1.  Add a JSON file to `templates/`.
2.  Ensure it follows the `ResearchTemplate` schema defined in `internal/research/models.py`.

---
*Generated by OpenCode Agent*
