# Markdown Chunking & Embedding System

A modular Python system for intelligently parsing, chunking, and embedding markdown documents into a Qdrant vector database.

## Config
- modify vectorize.yaml for custom chunking and embedding config
- modify search.yaml for search limit

## Running (Makefile)
- make up: start docker compose
- make e: extract pdf files to markdown
- make i: install the app dependency
- make v: chunk, embed and store the markdown to database
- make s: do RAG by query search

## Chunking Architecture
1. parsing markdown into AST (Abstract Syntax Tree) structure
2. build section hierarchy. Group all related elements under 1 Parent element. for example: header (#) is the bigger header so header (##, ###, list, tables) that are under it will be grouped into 1
3. chunking the section where each elements have their own chunking strategy, for example: if tables to large split by rows while still keep the table header

## Embedding Architecture
1. use Qdrant for vector store (dense and sparse) vector

## Retrieval Architecture
1. generate 2 embed query for sparse and dense vector for search
2. use Reciprocal Rank Fusion (RRF) for hybrid search
3. use reranker

## Directory structure
```
.
├── internal/
│   ├── cli/                      # Command-line interface logic
│   │   ├── config_loader.py      # Handles CLI-specific configurations
│   │   ├── display.py            # Formatting for terminal output
│   │   ├── search_cli.py         # Entry point for search queries
│   │   └── vectorize_cli.py      # Entry point for document processing/indexing
│   ├── core/                     # Shared business logic and orchestration
│   ├── embedding/                # Embedding & Ranking models
│   │   ├── dense_embedder.py     # Logic for dense vectors (e.g., OpenAI, HuggingFace)
│   │   ├── reranker.py           # Cross-encoder logic for result refinement
│   │   └── sparse_embedder.py    # Logic for sparse vectors (e.g., SPLADE, BM25)
│   ├── splitters/                # Document chunking strategies
│   │   ├── base_splitter.py      # Abstract base class for all splitters
│   │   ├── code_splitter.py      # Specialized splitting for source code
│   │   ├── list_splitter.py      # Handles bulleted/numbered lists
│   │   ├── table_splitter.py     # Preserves structure of tabular data
│   │   └── text_splitter.py      # Recursive/character-based text splitting
│   ├── storage/                  # Vector database integrations
│   │   └── qdrant_storage.py     # Qdrant-specific implementation
│   ├── text_processing/          # Global utilities for text cleanup
│   ├── config.py                 # Main application configuration
│   ├── logger.py                 # Centralized logging setup
│   ├── parser.py                 # Document loading and parsing logic
│   └── schema.py                 # Data models and Pydantic types
```