-- Initial schema for deep research system

-- Research templates store extraction schemas and prompts
CREATE TABLE IF NOT EXISTS research_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    schema_json JSONB NOT NULL,
    system_prompt TEXT,
    seed_questions JSONB
);

-- Research sessions track each research run
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    template_id UUID REFERENCES research_templates(id) NOT NULL,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'started',
    -- 'started', 'searching', 'crawling', 'processing', 'extracting', 'completed', 'failed'
    
    -- Progress metrics
    total_urls_found INTEGER DEFAULT 0,
    urls_crawled INTEGER DEFAULT 0,
    facts_extracted INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    -- Error tracking
    error_message TEXT
);

-- Search results from SearXNG queries
CREATE TABLE IF NOT EXISTS search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) NOT NULL,
    seed_question TEXT NOT NULL,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    url_hash TEXT,
    relevance_score FLOAT NOT NULL,
    domain TEXT,
    status TEXT DEFAULT 'pending',  -- 'pending', 'crawled', 'skipped', 'failed'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Raw documents crawled from URLs
CREATE TABLE IF NOT EXISTS raw_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_result_id UUID REFERENCES search_results(id) NOT NULL,
    content_type TEXT NOT NULL,     -- 'html', 'pdf', 'docx'
    raw_content BYTEA NOT NULL,     -- Binary storage
    content_hash TEXT UNIQUE,       -- Detect duplicate content
    crawl_status TEXT NOT NULL,     -- 'success', 'failed', 'timeout'
    error_message TEXT,
    crawled_at TIMESTAMP DEFAULT NOW()
);

-- Extracted facts from documents
CREATE TABLE IF NOT EXISTS research_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) NOT NULL,
    
    -- Vector store reference (Qdrant chunk ID)
    source_chunk_id TEXT NOT NULL,
    
    -- PostgreSQL reference for traceability
    source_document_id UUID REFERENCES raw_documents(id),
    source_url TEXT NOT NULL,
    
    -- Which seed question led to this fact
    seed_question TEXT,
    
    -- Extracted structured data matching template schema
    fact_data JSONB NOT NULL,
    
    -- LLM confidence assessment (0-1)
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1)
);