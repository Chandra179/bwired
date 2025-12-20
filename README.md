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
1. use Qdrant for vector store
2. use dense and sparse vector with Reciprocal Rank Fusion (RRF) for hybrid search