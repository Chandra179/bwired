# AI Agents - Deep Research System

A Python-based agentic AI research system with dynamic templating, recursive discovery, multi-format synthesis, and advanced document chunking.

![LLM Chat](test.png)

## Quick Start

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

## Architecture Overview

### Chunking Pipeline
1. Parse Markdown into AST (markdown-it-py)
2. Build section hierarchy - group elements under parent headers
3. Apply element-specific chunking:
   - Tables: split by rows, preserve headers
   - Code blocks: split by logical units
   - Lists: split by item groups
   - Text: split by tokens/paragraphs

### Research Pipeline Nodes
- **Initiation**: Generate seed questions from goal + template
- **Scout**: Search SearXNG for relevant URLs
- **Process**: Crawl URL → chunk → embed → extract facts
- **Discovery**: Identify leads → score links → generate sub-questions
- **Synthesis**: Aggregate facts → generate reports (table/graph/text/PDF)

## Documentation

- **AGENTS.md** - Detailed code standards, conventions, and technical specifications
- **TODO.md** - Implementation roadmap and task checklist
