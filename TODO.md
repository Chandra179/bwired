# Deep Research Implementation Roadmap

Implementation plan for adding deep research capabilities to the existing RAG system.

## Phase 1: Database & Infrastructure Setup (Week 1)

### 1.1 PostgreSQL Setup
- [x] Add PostgreSQL to `docker-compose.yml`
  ```yaml
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: bwired_research
      POSTGRES_USER: bwired
      POSTGRES_PASSWORD: <password>
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  ```

- [x] Create database schema migration file `migrations/001_initial_schema.sql`
  - `research_templates` table
  - `search_results` table
  - `raw_documents` table
  - `research_facts` table

- [x] Add PostgreSQL client to `requirements.txt`
  ```
  psycopg2-binary>=2.9.0
  asyncpg>=0.29.0  # For async operations
  ```

- [x] Create `internal/storage/postgres_client.py`
  - Connection management
  - Basic CRUD operations for templates
  - Research session tracking

### 1.2 SearXNG Setup
- [x] Add SearXNG to `docker-compose.yml`
  ```yaml
  searxng:
    image: searxng/searxng:latest
    ports:
      - "8080:8080"
    volumes:
      - ./searxng:/etc/searxng
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080/
  ```

- [x] Create SearXNG configuration file `searxng/settings.yml`
  - Enable required search engines
  - Configure rate limits
  - Set output format to JSON

### 1.3 Update Configuration
- [x] Add research section to `config.yaml`
  ```yaml
  research:
    postgres:
      host: "localhost"
      port: 5432
      database: "bwired_research"
      user: "bwired"
      password: "${POSTGRES_PASSWORD}"

    searxng:
      url: "http://localhost:8080"
      timeout: 30
      max_results_per_query: 10

    crawling:
      max_urls_per_domain: 5
      relevance_threshold: 50
      timeout: 30
      user_agent: "BwiredResearchBot/1.0"

    extraction:
      batch_size: 5
      confidence_threshold: 0.7
  ```

- [x] Update `internal/config.py` to include research configs
  - `ResearchConfig` dataclass
  - `PostgresConfig` dataclass
  - `SearXNGConfig` dataclass
  - `CrawlingConfig` dataclass

## Phase 2: Template Management (Week 1-2)

### 2.1 Template Data Models
- [ ] Create `internal/research/models.py`
  - `ResearchTemplate` Pydantic model
  - `TemplateSchema` for field definitions
  - `SeedQuestion` model
  - Validation logic for schema types

### 2.2 Template Manager
- [ ] Create `internal/research/template_manager.py`
  - `TemplateManager` class with:
    - `create_template(name, description, schema, prompts, seed_questions)`
    - `get_template(template_id)` 
    - `list_templates()`
    - `update_template(template_id, updates)`
    - `delete_template(template_id)`
    - `select_template(query)` - LLM-based template selection using descriptions

### 2.3 Default Templates
- [ ] Create `templates/historical_economy_events.json`
  ```json
  {
    "name": "historical_economy_events",
    "description": "Extract structured data from major historical economic shifts, crises, and systemic transformations.",
    "schema_json": {
        "fields": {
        "event_identity": {
            "type": "object",
            "properties": {
            "common_name": {"type": "string", "description": "Primary name (e.g., 'The Long Depression', 'The Nixon Shock')"},
            "start_year": {"type": "integer"},
            "end_year": {"type": "integer"},
            "geographic_scope": {"type": "string", "description": "Global, Regional, or National (specify countries)"}
            }
        },
        "classification": {
            "type": "string", 
            "description": "Category: Banking Crisis, Currency Crisis, Sovereign Debt, Hyperinflation, or Structural Shift"
        },
        "preceding_conditions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Factors present before the event (e.g., credit boom, low volatility, asset bubbles)"
        },
        "systemic_triggers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The 'Black Swan' or immediate catalyst (e.g., policy error, commodity shock, bank failure)"
        },
        "theoretical_impact": {
            "type": "string", 
            "description": "How this event changed economic thought (e.g., 'Shift from Classical to Keynesian economics')"
        }
      }
    },
    "system_prompt": "You are a senior macroeconomic historian. Your goal is to extract structured data that explains not just WHAT happened, but the systemic 'why' and the institutional 'aftermath'. Focus on quantifiable metrics where available and capture the qualitative shift in economic theory or regulation."
    }
  ```

- [ ] Add template loading script `scripts/load_templates.py`

## Phase 3: Search & URL Collection (Week 2)

### 3.1 SearXNG Integration
- [ ] Create `internal/research/search_orchestrator.py`
  - `SearchOrchestrator` class with:
    - `search(query, engines=None, max_results=10)` - call SearXNG API
    - `search_multiple(queries)` - batch search for seed questions
    - Error handling and retries
    - Response parsing and normalization

### 3.2 URL Processing
- [ ] Create `internal/research/url_processor.py`
  - `URLProcessor` class with:
    - `normalize_url(url)` - remove tracking params, lowercase, standardize
    - `calculate_hash(url)` - for deduplication
    - `score_relevance(url, title, query)` - scoring algorithm
    - `deduplicate_urls(url_list)` - remove duplicates
    - `filter_by_domain_limits(urls, max_per_domain=5)`

### 3.3 Relevance Scoring
- [ ] Implement scoring factors in `URLProcessor`:
  - Query match (0-40 points) - keyword overlap in URL/title
  - Domain authority (0-30 points) - .edu, .gov, known publishers
  - Freshness (0-15 points) - extract and score publication date
  - Content type (0-15 points) - prefer PDFs, research papers

- [ ] Add domain authority list
  - Create `data/trusted_domains.json` with scores
  - Academic: .edu, .ac.uk (30 points)
  - Government: .gov (30 points)  
  - Known publishers: nature.com, science.org (25 points)

### 3.4 Storage Integration
- [ ] Implement database operations in `postgres_client.py`:
  - `store_search_results(session_id, seed_question, urls)`
  - `get_pending_urls(session_id)`
  - `update_url_status(url_id, status)`

## Phase 4: Web Crawling (Week 2-3)

### 4.1 Crawl4AI Integration
- [ ] Add Crawl4AI to `requirements.txt`
  ```
  crawl4ai>=0.3.0
  playwright>=1.40.0  # Required by Crawl4AI
  ```

- [ ] Install Playwright browsers
  - Add to Makefile: `make install-browsers`
  - `playwright install chromium`

### 4.2 Web Crawler Implementation
- [ ] Create `internal/research/web_crawler.py`
  - `WebCrawler` class with:
    - `crawl_url(url, timeout=30)` - fetch content
    - `extract_content(html)` - get main content, remove boilerplate
    - `handle_pdf(url)` - special handling for PDF files
    - `calculate_content_hash(content)` - for duplicate detection
    - Error handling (timeouts, 404s, rate limits)

### 4.3 Content Storage
- [ ] Implement in `postgres_client.py`:
  - `store_raw_document(search_result_id, content_type, raw_content, hash)`
  - `check_content_hash(hash)` - detect duplicate content
  - `get_document_by_id(doc_id)`
  - `mark_crawl_failed(result_id, error_message)`

### 4.4 Crawling Orchestration
- [ ] Create `internal/research/crawl_orchestrator.py`
  - `CrawlOrchestrator` class with:
    - `crawl_batch(urls, batch_size=10)` - parallel crawling
    - `prioritize_urls(urls)` - sort by relevance score
    - Rate limiting logic
    - Progress tracking

## Phase 5: Content Processing Integration (Week 3)

### 5.1 Link Existing Chunking Pipeline
- [ ] Update `web_crawler.py` to use Docling
  - Convert crawled HTML/PDF to Markdown
  - Preserve tables, images, code blocks

- [ ] Update `crawl_orchestrator.py`
  - After crawling, trigger chunking pipeline
  - Use existing `ChunkerFactory.create(format='markdown')`
  - Store chunks with `research_session_id` metadata

### 5.2 Embedding & Vector Storage
- [ ] Update `internal/storage/qdrant_client.py`
  - Add `collection_name` parameter (support multiple collections)
  - Add method: `upsert_research_chunks(chunks, session_id)`
  - Include session_id in chunk metadata for filtering

- [ ] Create research-specific collection
  - Add to `research_pipeline.py`: create collection per session
  - Or use single collection with session_id filter

### 5.3 Metadata Enhancement
- [ ] Extend chunk metadata to include:
  ```python
  {
    "chunk_id": "uuid",
    "session_id": "research_session_uuid",
    "source_url": "https://...",
    "domain": "example.com",
    "seed_question": "What is...?",
    "crawl_timestamp": "2024-01-...",
    # existing metadata
    "section_path": "...",
    "parent_section": "...",
    "chunk_type": "text"
  }
  ```

## Phase 6: Fact Extraction (Week 3-4)

### 6.1 Instructor Integration
- [ ] Add Instructor to `requirements.txt`
  ```
  instructor>=1.0.0
  openai>=1.0.0  # Required by instructor
  ```

### 6.2 Fact Extractor Implementation
- [ ] Create `internal/research/fact_extractor.py`
  - `FactExtractor` class with:
    - `extract_from_chunk(chunk, template)` - use Instructor + Pydantic
    - `validate_extraction(facts, chunk_content)` - check hallucination
    - `calculate_confidence(facts)` - LLM self-assessment
    - Batch processing for multiple chunks

### 6.3 Dynamic Pydantic Models
- [ ] Create `internal/research/schema_builder.py`
  - `build_pydantic_model(template_schema)` - dynamically create model from JSON schema
  - Handle different field types (str, int, float, list, dict)
  - Add validation rules from schema

### 6.4 Retrieval for Extraction
- [ ] Create `internal/research/research_retriever.py`
  - `ResearchRetriever` class extending existing retriever
  - `retrieve_for_question(seed_question, session_id, top_k=10)`
  - Filter by session_id
  - Use hybrid search (dense + sparse)
  - Apply reranking

### 6.5 Fact Storage
- [ ] Implement in `postgres_client.py`:
  - `store_fact(session_id, chunk_id, source_url, fact_data, confidence)`
  - `get_facts_by_session(session_id, min_confidence=0.7)`
  - `get_facts_by_question(session_id, seed_question)`

## Phase 7: Research Pipeline Orchestration (Week 4)

### 7.1 Pipeline Implementation
- [ ] Create `internal/research/research_pipeline.py`
  - `ResearchPipeline` class orchestrating:
    1. Template selection
    2. Search execution (all seed questions)
    3. URL scoring and deduplication
    4. Crawling (prioritized batch)
    5. Content processing (chunking + embedding)
    6. Retrieval for each seed question
    7. Fact extraction
    8. Fact storage

### 7.2 Session Management
- [ ] Add to `postgres_client.py`:
  - `research_sessions` table operations
  - `create_session(query, template_id)` 
  - `update_session_status(session_id, status, progress)`
  - `get_session_info(session_id)`
  - Status: 'searching', 'crawling', 'processing', 'extracting', 'complete', 'failed'

### 7.3 Progress Tracking
- [ ] Implement progress updates:
  - Track: total URLs, crawled URLs, processed chunks, extracted facts
  - Store in `research_sessions` table
  - Update after each pipeline stage

### 7.4 Error Recovery
- [ ] Add basic error handling:
  - Log failures to database
  - Continue pipeline on partial failures
  - Mark failed URLs but don't stop entire research
  - Save partial results

## Phase 8: Synthesis & Report Generation (Week 4-5)

### 8.1 Fact Aggregation
- [ ] Create `internal/research/synthesizer.py`
  - `ResearchSynthesizer` class with:
    - `aggregate_facts(session_id)` - group by seed question
    - `format_for_llm(facts)` - prepare facts for synthesis
    - `count_sources(facts)` - track source diversity

### 8.2 Report Generation
- [ ] Implement in `ResearchSynthesizer`:
  - `generate_report(session_id, format='markdown')`
  - Use LLM to synthesize facts into coherent narrative
  - Include source citations
  - Group findings by theme
  - Highlight key insights

### 8.3 Report Templates
- [ ] Create Jinja2 templates in `templates/reports/`:
  - `executive_summary.md.jinja2`
  - `detailed_findings.md.jinja2`
  - `sources_cited.md.jinja2`

## Phase 9: API Endpoints (Week 5)

### 9.1 Research API
- [ ] Create `internal/server/research_api.py`
  - `POST /research/start` - initiate research
    ```json
    {
      "query": "What is the efficacy of...",
      "template_name": "clinical_studies"  // optional, auto-select if not provided
    }
    ```
  
  - `GET /research/{session_id}/status` - check progress
    ```json
    {
      "session_id": "uuid",
      "status": "extracting",
      "progress": {
        "urls_found": 45,
        "urls_crawled": 30,
        "chunks_processed": 250,
        "facts_extracted": 89
      }
    }
    ```
  
  - `GET /research/{session_id}/facts` - get raw facts
  - `GET /research/{session_id}/report` - get synthesized report

### 9.2 Template API
- [ ] Add template management endpoints:
  - `POST /research/templates` - create template
  - `GET /research/templates` - list all
  - `GET /research/templates/{id}` - get specific
  - `PUT /research/templates/{id}` - update
  - `DELETE /research/templates/{id}` - delete

### 9.3 Server Integration
- [ ] Update `internal/server/server.py` lifespan:
  - Initialize PostgreSQL client
  - Initialize research components
  - Include in server state

## Phase 10: Testing & Refinement (Week 5-6)

### 10.1 Integration Testing
- [ ] Create `tests/test_research_pipeline.py`
  - Test end-to-end with simple query
  - Verify each stage completes
  - Check fact extraction quality

### 10.2 Performance Testing
- [ ] Test with various query types:
  - Simple factual queries (10-20 URLs)
  - Complex research (50+ URLs)
  - Measure time per stage

### 10.3 Quality Checks
- [ ] Manual review of:
  - Template selection accuracy
  - URL relevance scoring
  - Fact extraction quality
  - Report coherence

### 10.4 Documentation
- [ ] Update README with examples
- [ ] Create API documentation (Swagger/OpenAPI)
- [ ] Write user guide for creating templates
- [ ] Add troubleshooting section

## Quick Start Checklist (MVP)

For a minimal working version, focus on these tasks first:

- [x] Phase 1.1: PostgreSQL setup + basic schema
- [x] Phase 1.3: Basic research config
- [ ] Phase 2.2: Simple template manager (hardcoded template OK for MVP)
- [ ] Phase 3.1: SearXNG integration (basic search only)
- [ ] Phase 4.2: Web crawler (HTML only, skip PDFs for MVP)
- [ ] Phase 5.1: Link to existing chunking
- [ ] Phase 6.2: Basic fact extraction (simple Pydantic model)
- [ ] Phase 7.1: Minimal pipeline (no progress tracking)
- [ ] Phase 8.2: Simple report (just concatenate facts)
- [ ] Phase 9.1: Single endpoint: `POST /research/start` returns final report

**Estimated MVP time**: 2-3 weeks with focused effort

## Notes

- Keep existing RAG functionality working while adding research features
- Test each phase independently before moving to next
- Use existing chunking/embedding infrastructure - don't rebuild it
- Start with one good template (clinical studies) before generalizing
- Defer optimization until basic flow works end-to-end