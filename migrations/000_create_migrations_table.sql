CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS research_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    schema_json JSONB NOT NULL,
    system_prompt TEXT,
    seed_questions JSONB
);

CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    template_id UUID REFERENCES research_templates(id) NOT NULL,
    status TEXT NOT NULL DEFAULT 'started',
    total_urls_found INTEGER DEFAULT 0,
    urls_crawled INTEGER DEFAULT 0,
    facts_extracted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) NOT NULL,
    seed_question TEXT NOT NULL,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    url_hash TEXT,
    relevance_score FLOAT NOT NULL,
    domain TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_result_id UUID REFERENCES search_results(id) NOT NULL,
    content_type TEXT NOT NULL,
    raw_content BYTEA NOT NULL,
    content_hash TEXT UNIQUE,
    crawl_status TEXT NOT NULL,
    error_message TEXT,
    crawled_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS research_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) NOT NULL,
    source_chunk_id TEXT NOT NULL,
    source_document_id UUID REFERENCES raw_documents(id),
    source_url TEXT NOT NULL,
    seed_question TEXT,
    fact_data JSONB NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

CREATE TABLE IF NOT EXISTS research_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE UNIQUE,
    executive_summary_overview TEXT,
    executive_summary_conclusions JSONB,
    executive_summary_confidence VARCHAR(20),
    sections JSONB NOT NULL,
    sections_count INTEGER NOT NULL,
    key_insights JSONB NOT NULL,
    insights_count INTEGER NOT NULL,
    total_facts_analyzed INTEGER NOT NULL,
    unique_sources_count INTEGER NOT NULL,
    avg_confidence FLOAT,
    domain_counts JSONB,
    generated_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_session ON research_reports(session_id);

CREATE OR REPLACE FUNCTION update_report_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_report_updated_at ON research_reports;
CREATE TRIGGER trigger_update_report_updated_at
    BEFORE UPDATE ON research_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_report_updated_at();
