# Markdown Chunking & Embedding System

A modular Python system for intelligently parsing, chunking, and embedding markdown documents into a Qdrant vector database.

## Features

- 🎯 **Smart Chunking**: Respects markdown structure (headers, tables, lists, code blocks)
- 🔢 **Token-Aware**: Uses model's tokenizer for accurate token counting
- 📊 **Content-Specific Rules**: Different strategies for tables, lists, paragraphs, images
- 🔄 **Context Preservation**: Adds overlap between chunks and includes header hierarchy
- 🚀 **Embedding Generation**: Uses BAAI/bge-base-en-v1.5 or any HuggingFace model
- 💾 **Vector Storage**: Direct integration with Qdrant vector database
- 🛠️ **Modular Design**: Easy to extend and customize

## Usage

### Basic Command

```bash
python -m markdown_chunker.cli --input document.md --qdrant-url http://localhost:6333
```

### Common Examples

**1. Process with custom collection name:**
```bash
python -m markdown_chunker.cli \
  --input report.md \
  --collection-name my_documents \
  --document-title "Q4 Financial Report"
```

**2. Customize chunking parameters:**
```bash
python -m markdown_chunker.cli \
  --input large_doc.md \
  --target-chunk-size 300 \
  --overlap-tokens 75 \
  --max-tokens 512
```

**3. Use GPU for faster embedding:**
```bash
python -m markdown_chunker.cli \
  --input document.md \
  --device cuda
```

**4. Dry run (parse and chunk without storing):**
```bash
python -m markdown_chunker.cli \
  --input document.md \
  --dry-run
```

### Using Config File

Create a `config.yaml`:

```yaml
# Embedding configuration
model_name: "BAAI/bge-base-en-v1.5"
max_token_limit: 512
target_chunk_size: 400
min_chunk_size: 100
overlap_tokens: 50
device: "cpu"

# Qdrant configuration
qdrant_url: "http://localhost:6333"
collection_name: "markdown_docs"
distance_metric: "Cosine"
```

Then run:

```bash
python -m markdown_chunker.cli --input document.md --config config.yaml
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input`, `-i` | Path to markdown file | **Required** |
| `--qdrant-url` | Qdrant server URL | `http://localhost:6333` |
| `--collection-name` | Collection name | `markdown_chunks` |
| `--api-key` | Qdrant API key | None |
| `--model` | HuggingFace model | `BAAI/bge-base-en-v1.5` |
| `--device` | Device (cpu/cuda) | `cpu` |
| `--max-tokens` | Max token limit | `512` |
| `--target-chunk-size` | Target chunk size | `400` |
| `--min-chunk-size` | Min chunk size | `100` |
| `--overlap-tokens` | Overlap tokens | `50` |
| `--document-id` | Document ID | Filename stem |
| `--document-title` | Document title | Filename |
| `--config` | Config file path | None |
| `--log-level` | Logging level | `INFO` |
| `--log-file` | Log file path | None |
| `--dry-run` | Parse without storing | `False` |
| `--show-collection-info` | Show collection info | `False` |

```
# Basic search
python -m markdown_chunker.cli --search "what's political economy situation between china and india"

# With custom limit
python -m markdown_chunker.cli --search "climate change" --search-limit 10

# Filter by document
python -m markdown_chunker.cli --search "revenue" --filter-document report_2024

# With custom collection
python -m markdown_chunker.cli --search "query" --collection-name my_docs --qdrant-url http://localhost:6333
```

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
9. **cli.py**: Command-line interface
9. **extract_doc.py**: Extract docs to target file (markdown, etc..)

## Performance Tips

1. **GPU Acceleration**: Use `--device cuda` for ~5-10x faster embedding generation
2. **Batch Processing**: Process multiple files by running CLI in a loop
3. **Token Limits**: Adjust `--target-chunk-size` based on your use case
4. **Overlap**: Increase `--overlap-tokens` for better context preservation
