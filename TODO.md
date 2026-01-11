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
- [ ] Add Crawl4AI integration
  - [ ] Create `internal/search/crawl4ai_client.py`
  - [ ] Implement `fetch_url(url)` → Markdown
  - [ ] Add `Crawl4AIConfig` to `config.yaml`

### Semantic Chunking
- [ ] Verify existing markdown chunker supports header-based splitting
  - [ ] Ensure headers (`#`, `##`) define chunk boundaries
  - [ ] Validate token counting accuracy

### Vector Embedding
- [ ] Verify pgvector support
  - [ ] Create PostgreSQL extension for pgvector
  - [ ] Define 1536-dimensional vector column
  - [ ] Add HNSW index for fast similarity search

### Fact Extraction
- [ ] Create `internal/research/nodes/process.py`
  - [ ] Implement `extract_facts(markdown, schema_model)` using Instructor
  - [ ] LLM populates dynamic Pydantic schema
  - [ ] Return structured facts as JSONB
- [ ] Store results in `extracted_facts` column (JSONB type)

---

## 3. Recursive Discovery & Lead Identification

### Lead Identification
- [ ] Create `internal/research/lead_extractor.py`
  - [ ] Implement `extract_citations(extracted_facts, markdown)`
  - [ ] Parse links and references from Markdown
  - [ ] Identify mentions without details (conceptual leads)
- [ ] Implement `generate_sub_questions(concept, original_goal)`
  - [ ] Create new research questions for unknown concepts

### Link Extraction & Priority
- [ ] Implement link extraction from Markdown
  - [ ] Parse anchor text and URLs
  - [ ] Deduplicate URLs
- [ ] Implement priority scoring
  - [ ] Embed anchor text into vector
  - [ ] Calculate cosine similarity with original question vector
  - [ ] Score range: 0.0 to 1.0
- [ ] Implement pruning logic
  - [ ] Discard links with score < 0.5
  - [ ] Discard links exceeding depth limit

### Redis Priority Queue
- [ ] Create `internal/queue/task_queue.py`
  - [ ] Initialize Redis connection
  - [ ] Implement `push_task(task_type, priority, payload)`
  - [ ] Implement `pop_task()` returns highest priority
  - [ ] Task types: "Scout", "Process", "Discovery"
- [ ] Create `internal/queue/redis_client.py`
  - [ ] Configure Redis client
  - [ ] Add connection pooling

### Discovery Node
- [ ] Create `internal/research/nodes/discovery.py`
  - [ ] Process `extracted_facts` to identify leads
  - [ ] Extract and score links
  - [ ] Generate new sub-questions
  - [ ] Push valid tasks to Redis queue

---

## 4. Storage Strategy

### Database Tables
- [ ] Create `research_nodes` table
  - Columns:
    - `id` (UUID)
    - `task_id` (FK to research_tasks)
    - `parent_node_id` (FK to research_nodes, self-referencing)
    - `node_type` (initiation, scout, process, discovery)
    - `url` (nullable, for crawled pages)
    - `question_text` (for research questions)
    - `depth_level` (integer)
    - `extracted_facts` (JSONB)
    - `content_vector` (pgvector, 1536 dims)
    - `priority_score` (float, 0.0-1.0)
    - `status` (pending, processing, completed, failed)
    - `created_at`, `updated_at`

### Indexes
- [ ] Create HNSW index on `content_vector` for similarity search
- [ ] Create B-tree index on `url` for deduplication
- [ ] Create B-tree index on `question_text` for deduplication
- [ ] Create index on `parent_node_id` for lineage queries
- [ ] Create index on `task_id` for task-level queries
- [ ] Create index on `status` for filtering

### ORM Models
- [ ] Create `internal/database/models.py`
  - [ ] Define SQLAlchemy models for all tables
  - [ ] Set up relationships (parent-child lineage)
  - [ ] Add JSONB and pgvector column types

### Database Client
- [ ] Create `internal/database/client.py`
  - [ ] Initialize async SQLAlchemy engine
  - [ ] Create session factory
  - [ ] Implement CRUD operations for nodes
  - [ ] Implement vector similarity queries

---

## 5. Presentation & Synthesis

### Synthesis Node
- [ ] Create `internal/research/nodes/synthesis.py`
  - [ ] Implement `collect_facts(task_id)`
    - [ ] Query all completed nodes for task
    - [ ] Aggregate `extracted_facts` from JSONB columns
  - [ ] Implement depth check
    - [ ] Verify queue is empty OR depth limit reached
    - [ ] Mark task as "synthesis_ready"

### Table Format
- [ ] Implement `flatten_to_table(facts_list)`
  - [ ] Extract all unique keys from JSONB objects
  - [ ] Create header row from keys
  - [ ] Create data rows
  - [ ] Support CSV and Markdown output

### Graph Format
- [ ] Implement `build_lineage_graph(task_id)`
  - [ ] Query nodes with `parent_node_id` relationships
  - [ ] Generate Mermaid.js diagram
    - [ ] Nodes = research topics
    - [ ] Edges = lineage connections
  - [ ] Optionally generate D3.js visualization

### Text/PDF Report
- [ ] Implement `generate_narrative(facts_list, goal)`
  - [ ] Use LLM to write cohesive story
  - [ ] Use ONLY `extracted_facts` as source (reduce hallucinations)
  - [ ] Structure: Introduction → Key Findings → Connections → Conclusion
  - [ ] Support Markdown and PDF output

### API Endpoints
- [ ] Add GET `/research/{task_id}`
  - [ ] Return task status (pending, processing, synthesis_ready, completed)
  - [ ] Return progress statistics
- [ ] Add GET `/research/{task_id}/result?format={table|graph|text|pdf}`
  - [ ] Query and aggregate facts
  - [ ] Generate requested format
  - [ ] Return appropriate Content-Type

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
