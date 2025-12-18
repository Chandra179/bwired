# Markdown Chunking & Embedding System

A modular Python system for intelligently parsing, chunking, and embedding markdown documents into a Qdrant vector database.

## Features

- 🎯 **Smart Chunking**: Respects markdown structure (headers, tables, lists, code blocks)
- 🔢 **Token-Aware**: Uses model's tokenizer for accurate token counting
- 📊 **Content-Specific Rules**: Different strategies for tables, lists, paragraphs, images
- 🔄 **Context Preservation**: Adds overlap between chunks and includes header hierarchy
- 🚀 **Embedding Generation**: Uses BAAI/bge-base-en-v1.5 or any HuggingFace model
- 💾 **Vector Storage**: Direct integration with Qdrant vector database
- 🔍 **Vector Search**: Fast semantic search across your documents
- 🛠️ **Modular Design**: Easy to extend and customize
- ⚙️ **Config-Driven**: YAML configuration for easy management

## Quick Start

### 1. Vectorize Documents

Create a `vectorize.yaml` config file:

```yaml
# Embedding Model Configuration
model_name: "BAAI/bge-base-en-v1.5"
device: "cpu"
max_token_limit: 512

# Chunking Parameters
target_chunk_size: 400
min_chunk_size: 100
overlap_tokens: 50

# Qdrant Configuration
qdrant_url: "http://localhost:6333"
collection_name: "markdown_docs"
distance_metric: "Cosine"

# Logging
log_level: "INFO"
```

Then run:

```bash
python -m markdown_chunker.vectorize --input document.md --config vectorize.yaml
```

### 2. Search Documents

Create a `search.yaml` config file:

```yaml
# Embedding Model Configuration
model_name: "BAAI/bge-base-en-v1.5"
device: "cpu"

# Qdrant Configuration
qdrant_url: "http://localhost:6333"
collection_name: "markdown_docs"

# Search Parameters
search_limit: 5
# score_threshold: 0.7
# filter_document: "report_2024"

# Logging
log_level: "INFO"
```

Then search:

```bash
python -m markdown_chunker.search --config search.yaml --query "what is the political situation"
```

## Usage Examples

### Vectorization

**Basic vectorization:**
```bash
python -m markdown_chunker.vectorize --input report.md --config vectorize.yaml
```

**With custom document title:**
```bash
python -m markdown_chunker.vectorize \
  --input report.md \
  --config vectorize.yaml \
  --document-title "Q4 Financial Report"
```

**With GPU acceleration (edit vectorize.yaml):**
```yaml
device: "cuda"  # Change from "cpu" to "cuda"
```

### Search

**Basic search:**
```bash
python -m markdown_chunker.search \
  --config search.yaml \
  --query "what are the main findings"
```

**Search with filters (edit search.yaml):**
```yaml
# Filter by specific document
filter_document: "report_2024"

# Filter by heading
filter_heading: "Introduction"

# Set score threshold
score_threshold: 0.75

# Increase result limit
search_limit: 10
```

## Configuration Files

### vectorize.yaml

| Parameter | Description | Default |
|-----------|-------------|---------|
| `model_name` | HuggingFace model name | `BAAI/bge-base-en-v1.5` |
| `device` | Device for embedding (cpu/cuda) | `cpu` |
| `max_token_limit` | Maximum token limit | `512` |
| `target_chunk_size` | Target chunk size in tokens | `400` |
| `min_chunk_size` | Minimum chunk size in tokens | `100` |
| `overlap_tokens` | Overlap between chunks | `50` |
| `qdrant_url` | Qdrant server URL | `http://localhost:6333` |
| `collection_name` | Collection name | `markdown_docs` |
| `distance_metric` | Distance metric (Cosine/Euclid/Dot) | `Cosine` |
| `log_level` | Logging level | `INFO` |
| `log_file` | Log file path (optional) | None |

### search.yaml

| Parameter | Description | Default |
|-----------|-------------|---------|
| `model_name` | HuggingFace model (must match vectorization) | `BAAI/bge-base-en-v1.5` |
| `device` | Device for embedding (cpu/cuda) | `cpu` |
| `max_token_limit` | Maximum token limit | `512` |
| `qdrant_url` | Qdrant server URL | `http://localhost:6333` |
| `collection_name` | Collection name | `markdown_docs` |
| `search_limit` | Maximum number of results | `5` |
| `score_threshold` | Minimum similarity score (0.0-1.0) | None |
| `filter_document` | Filter by document ID | None |
| `filter_heading` | Filter by heading | None |
| `log_level` | Logging level | `INFO` |
| `log_file` | Log file path (optional) | None |

## Architecture

### Module Overview

1. **config.py**: Configuration dataclasses for embedding and Qdrant settings
2. **parser.py**: Markdown parsing and element identification
3. **tokenizer_utils.py**: Token counting using model's tokenizer
4. **chunker.py**: Core chunking logic with content-type specific rules
5. **embedder.py**: Embedding generation using transformers
6. **metadata.py**: Metadata schema for vector storage
7. **storage.py**: Qdrant client and storage operations
8. **utils.py**: Helper functions
9. **vectorize.py**: Command-line interface for vectorization
10. **search.py**: Command-line interface for vector search

## Performance Tips

1. **GPU Acceleration**: Set `device: "cuda"` in config for ~5-10x faster embedding generation
2. **Batch Processing**: Process multiple files by running vectorize in a loop
3. **Token Limits**: Adjust `target_chunk_size` based on your use case
4. **Overlap**: Increase `overlap_tokens` for better context preservation
5. **Search Optimization**: Use `score_threshold` and filters to refine results

## Advanced Usage

### Multiple Collections

Create different config files for different collections:

**technical_docs.yaml:**
```yaml
collection_name: "technical_docs"
target_chunk_size: 300
```

**marketing_content.yaml:**
```yaml
collection_name: "marketing_content"
target_chunk_size: 500
```

### Custom Models

Use different embedding models:

```yaml
model_name: "sentence-transformers/all-MiniLM-L6-v2"
max_token_limit: 256
```

**Note:** Ensure you use the same model for both vectorization and search!

## Workflow Example

```bash
# 1. Vectorize multiple documents
python -m markdown_chunker.vectorize --input docs/intro.md --config vectorize.yaml
python -m markdown_chunker.vectorize --input docs/guide.md --config vectorize.yaml
python -m markdown_chunker.vectorize --input docs/api.md --config vectorize.yaml

# 2. Search across all documents
python -m markdown_chunker.search --config search.yaml --query "authentication"

# 3. Search within specific document (edit search.yaml first)
# Add: filter_document: "guide"
python -m markdown_chunker.search --config search.yaml --query "getting started"
```

## Requirements

- Python 3.8+
- PyTorch
- Transformers
- Qdrant Client
- PyYAML
- Other dependencies (see requirements.txt)

## Installation

```bash
pip install -r requirements.txt
```