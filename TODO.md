# Deep Research - Implementation TODO

## Overview
This TODO list outlines the implementation of a Deep Research agent system with dynamic templating, recursive discovery, and multi-format synthesis.

---

## 0. Technical Stack Setup

### Dependencies
- [x] Add PostgreSQL dependencies: `asyncpg>=0.29.0`, `sqlalchemy>=2.0.0`, `pgvector>=0.3.0`
- [x] Add Redis dependencies: `redis>=5.0.0`, `hiredis>=2.3.0`
- [x] Add structured extraction: `instructor>=1.0.0`
- [x] Add web scraping: `crawl4ai>=0.4.0`
- [x] Add graph visualization (optional): `pyvis>=0.3.0`

### Infrastructure
- [x] Update `docker-compose.yml` with PostgreSQL, Redis, and SearXNG services
- [x] Configure PostgreSQL with pgvector extension
- [x] Configure Redis for priority queues
- [x] Set up SearXNG instance for multi-engine search

---

## 1. Initiation & Dynamic Templating

### Database Schema
- [x] Create `templates` table in PostgreSQL
  - Columns: `id`, `name`, `description`, `schema_json` (JSONB), `created_at`
- [x] Create `research_tasks` table
  - Columns: `id`, `goal`, `template_id`, `depth_limit`, `status`, `created_at`
- [x] Add indexes on `template_id`, `status`, `created_at`

### Dynamic Schema Generation
- [x] Create `internal/research/schema_factory.py`
  - [x] Implement `create_dynamic_model(schema_json)` using `pydantic.create_model()`
  - [x] Add type mapping (str, int, float, list, dict)
  - [x] Handle nested schemas

### Seed Question Generation
- [x] Create `internal/research/nodes/initiation.py`
  - [x] Implement `generate_seed_questions(goal, template, count=3-5)`
  - [x] Use LLM to generate questions based on template fields
  - [x] Return list of question texts

### API Endpoint
- [x] Add POST `/research/start` endpoint
  - [x] Accept: `goal`, `template_id`, `depth_limit`
  - [x] Validate template exists
  - [x] Create research task record
  - [x] Generate seed questions
  - [x] Return `task_id`

---

## 2. Processing Pipeline (HTML to Fact)

### Document Extraction
- [x] Add Crawl4AI integration
  - [x] Create `internal/search/crawl4ai_client.py`
  - [x] Implement `fetch_url(url)` → Markdown
  - [x] Add `Crawl4AIConfig` to `config.yaml`

### Semantic Chunking
- [x] Verify existing markdown chunker supports header-based splitting
  - [x] Ensure headers (`#`, `##`) define chunk boundaries
  - [x] Validate token counting accuracy

### Vector Embedding
- [x] Verify pgvector support
  - [x] Create PostgreSQL extension for pgvector
  - [x] Define 768-dimensional vector column
  - [x] Add HNSW index for fast similarity search

### Fact Extraction
- [x] Create `internal/research/nodes/process.py`
  - [x] Implement `extract_facts(markdown, schema_model)` using Instructor
  - [x] LLM populates dynamic Pydantic schema
  - [x] Return structured facts as JSONB
- [x] Store results in `extracted_facts` column (JSONB type)

---

## 3. Recursive Discovery & Lead Identification

### Lead Identification
- [x] Create `internal/research/lead_extractor.py`
  - [x] Implement `extract_citations(extracted_facts, markdown)`
  - [x] Parse links and references from Markdown
  - [x] Identify mentions without details (conceptual leads)
- [x] Implement `generate_sub_questions(concept, original_goal)`
  - [x] Create new research questions for unknown concepts

### Link Extraction & Priority
- [x] Implement link extraction from Markdown
  - [x] Parse anchor text and URLs
  - [x] Deduplicate URLs
- [x] Implement priority scoring
  - [x] Embed anchor text into vector
  - [x] Calculate cosine similarity with original question vector
  - [x] Score range: 0.0 to 1.0
- [x] Implement pruning logic
  - [x] Discard links with score < 0.5
  - [x] Discard links exceeding depth limit

### Redis Priority Queue
- [x] Create `internal/queue/task_queue.py`
  - [x] Initialize Redis connection
  - [x] Implement `push_task(task_type, priority, payload)`
  - [x] Implement `pop_task()` returns highest priority
  - [x] Task types: "scout", "process", "discovery"
- [x] Create `internal/queue/redis_client.py`
  - [x] Configure Redis client
  - [x] Add connection pooling

### Discovery Node
- [x] Create `internal/research/nodes/discovery.py`
- [x] Process `extracted_facts` to identify leads
- [x] Extract and score links
- [x] Generate new sub-questions
- [x] Push valid tasks to Redis queue

---

## 4. Storage Strategy

### Database Tables
- [x] Create `research_nodes` table
  - Columns:
    - `id` (UUID)
    - `task_id` (FK to research_tasks)
    - `parent_node_id` (FK to research_nodes, self-referencing)
    - `node_type` (initiation, scout, process, discovery)
    - `url` (nullable, for crawled pages)
    - `question_text` (for research questions)
    - `depth_level` (integer)
    - `extracted_facts` (JSONB)
    - `content_vector` (pgvector, 768 dims)
    - `priority_score` (float, 0.0-1.0)
    - `status` (pending, processing, completed, failed)
    - `created_at`, `updated_at`

### Indexes
- [x] Create HNSW index on `content_vector` for similarity search
- [x] Create B-tree index on `url` for deduplication
- [x] Create B-tree index on `question_text` for deduplication
- [x] Create index on `parent_node_id` for lineage queries
- [x] Create index on `task_id` for task-level queries
- [x] Create index on `status` for filtering

### ORM Models
- [x] Create `internal/database/models.py`
  - [x] Define SQLAlchemy models for all tables
  - [x] Set up relationships (parent-child lineage)
  - [x] Add JSONB and pgvector column types

### Database Client
- [x] Create `internal/database/client.py`
  - [x] Initialize async SQLAlchemy engine
  - [x] Create session factory
  - [x] Implement CRUD operations for nodes
  - [x] Implement vector similarity queries

---

## 5. Presentation & Synthesis

### Synthesis Node
- [x] Create `internal/research/nodes/synthesis.py`
  - [x] Implement `collect_facts(task_id)`
    - [x] Query all completed nodes for task
    - [x] Aggregate `extracted_facts` from JSONB columns
  - [x] Implement depth check
    - [x] Verify queue is empty OR depth limit reached
    - [x] Mark task as "synthesis_ready"

### Table Format
- [x] Implement `flatten_to_table(facts_list)`
  - [x] Extract all unique keys from JSONB objects
  - [x] Create header row from keys
  - [x] Create data rows
  - [x] Support CSV and Markdown output

### Graph Format
- [x] Implement `build_lineage_graph(task_id)`
  - [x] Query nodes with `parent_node_id` relationships
  - [x] Generate Mermaid.js diagram
    - [x] Nodes = research topics
    - [x] Edges = lineage connections
  - [ ] Optionally generate D3.js visualization

### Text/PDF Report
- [x] Implement `generate_narrative(facts_list, goal)`
  - [x] Use LLM to write cohesive story
  - [x] Use ONLY `extracted_facts` as source (reduce hallucinations)
  - [x] Structure: Introduction → Key Findings → Connections → Conclusion
  - [ ] Support Markdown and PDF output

### API Endpoints
- [x] Add GET `/research/{task_id}`
  - [x] Return task status (pending, processing, synthesis_ready, completed)
  - [x] Return progress statistics
- [x] Add GET `/research/{task_id}/result?format={table|graph|text}`
  - [x] Query and aggregate facts
  - [x] Generate requested format
  - [x] Return appropriate Content-Type

---

## Configuration Updates

### config.yaml
```yaml
# Add these sections
postgres:
  url: "postgresql+asyncpg://researcher:password@localhost:5432/deep_research"
  pool_size: 10
  max_overflow: 20

redis:
  url: "redis://localhost:6379/0"
  db: 0
  max_connections: 50

searxng:
  api_url: "http://localhost:8080/search"
  timeout: 30

crawl4ai:
  browser_type: "chromium"
  headless: true
  timeout: 30

research:
  default_depth_limit: 3
  max_pages_per_task: 100
  priority_threshold: 0.5
  seed_question_count: 5

synthesis:
  llm_temperature: 0.3
  max_output_tokens: 4000
```

---

## Implementation Order

1. **Foundation**: Database setup, Redis, dependencies
2. **Initiation**: Templates, dynamic schemas, seed questions
3. **Processing**: Crawl4AI, fact extraction, storage
4. **Discovery**: Lead identification, link extraction, priority queue
5. **Synthesis**: Report generation, API endpoints
6. **Integration**: End-to-end pipeline testing
