"""Database models and SQL DDL definitions for PostgreSQL and SQLite.

Includes clearly namespaced AI-service tables:
- ai_documents
- ai_processing_jobs
- ai_financial_metrics
- ai_metric_evidence
- ai_red_flag_findings
- ai_agent_runs
Along with backward-compatible definitions for legacy development tables.
"""

POSTGRES_SCHEMA_SQL = """
-- PostgreSQL Schema for Supabase (AI Service Namespace)

CREATE TABLE IF NOT EXISTS ai_documents (
    document_id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64),
    session_id VARCHAR(64),
    user_id VARCHAR(64),
    sha256 VARCHAR(64) NOT NULL UNIQUE,
    filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    total_pages INTEGER DEFAULT 0,
    total_characters INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    indexed INTEGER DEFAULT 0,
    mime_type VARCHAR(64) DEFAULT 'application/pdf',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_documents_sha256 ON ai_documents(sha256);
CREATE INDEX IF NOT EXISTS idx_ai_documents_session ON ai_documents(session_id);

CREATE TABLE IF NOT EXISTS ai_processing_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES ai_documents(document_id) ON DELETE CASCADE,
    workspace_id VARCHAR(64),
    session_id VARCHAR(64),
    status VARCHAR(32) NOT NULL,
    current_stage VARCHAR(64) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_financial_metrics (
    metric_id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES ai_documents(document_id) ON DELETE CASCADE,
    period_type VARCHAR(32) DEFAULT 'ANNUAL',
    fiscal_year INTEGER NOT NULL,
    statement_type VARCHAR(64) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    source_label VARCHAR(255),
    numeric_value NUMERIC(24, 4) NOT NULL,
    currency VARCHAR(16) DEFAULT 'INR',
    unit VARCHAR(32) DEFAULT 'CRORES',
    is_calculated BOOLEAN DEFAULT FALSE,
    formula TEXT,
    is_consolidated BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_metrics_doc ON ai_financial_metrics(document_id);

CREATE TABLE IF NOT EXISTS ai_metric_evidence (
    evidence_id VARCHAR(64) PRIMARY KEY,
    metric_id VARCHAR(64) REFERENCES ai_financial_metrics(metric_id) ON DELETE CASCADE,
    document_id VARCHAR(64) REFERENCES ai_documents(document_id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    exact_quote TEXT NOT NULL,
    table_index INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_red_flag_findings (
    finding_id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES ai_documents(document_id) ON DELETE CASCADE,
    session_id VARCHAR(64),
    category VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    detection_method VARCHAR(32) DEFAULT 'RULE_BASED',
    supporting_evidence TEXT NOT NULL,
    source_page INTEGER NOT NULL,
    requires_review BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_red_flags_doc ON ai_red_flag_findings(document_id);

CREATE TABLE IF NOT EXISTS ai_agent_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES ai_documents(document_id) ON DELETE CASCADE,
    session_id VARCHAR(64),
    agent_name VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    input_payload JSONB DEFAULT '{}'::jsonb,
    output_payload JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Legacy development tables maintained for backward compatibility
CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    document_id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64),
    sha256 VARCHAR(64) NOT NULL UNIQUE,
    filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    total_pages INTEGER DEFAULT 0,
    total_characters INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    indexed INTEGER DEFAULT 0,
    mime_type VARCHAR(64) DEFAULT 'application/pdf',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_documents (
    session_id VARCHAR(64) REFERENCES research_sessions(session_id) ON DELETE CASCADE,
    document_id VARCHAR(64) REFERENCES documents(document_id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, document_id)
);
"""

SQLITE_SCHEMA_SQL = """
-- SQLite Schema for Local Development & Testing

CREATE TABLE IF NOT EXISTS ai_documents (
    document_id TEXT PRIMARY KEY,
    workspace_id TEXT,
    session_id TEXT,
    user_id TEXT,
    sha256 TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    total_pages INTEGER DEFAULT 0,
    total_characters INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    indexed INTEGER DEFAULT 0,
    mime_type TEXT DEFAULT 'application/pdf',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_processing_jobs (
    job_id TEXT PRIMARY KEY,
    document_id TEXT,
    workspace_id TEXT,
    session_id TEXT,
    status TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES ai_documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_financial_metrics (
    metric_id TEXT PRIMARY KEY,
    document_id TEXT,
    period_type TEXT DEFAULT 'ANNUAL',
    fiscal_year INTEGER NOT NULL,
    statement_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    source_label TEXT,
    numeric_value TEXT NOT NULL,
    currency TEXT DEFAULT 'INR',
    unit TEXT DEFAULT 'CRORES',
    is_calculated INTEGER DEFAULT 0,
    formula TEXT,
    is_consolidated INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES ai_documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_metric_evidence (
    evidence_id TEXT PRIMARY KEY,
    metric_id TEXT,
    document_id TEXT,
    page_number INTEGER NOT NULL,
    exact_quote TEXT NOT NULL,
    table_index INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(metric_id) REFERENCES ai_financial_metrics(metric_id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES ai_documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_red_flag_findings (
    finding_id TEXT PRIMARY KEY,
    document_id TEXT,
    session_id TEXT,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    detection_method TEXT DEFAULT 'RULE_BASED',
    supporting_evidence TEXT NOT NULL,
    source_page INTEGER NOT NULL,
    requires_review INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES ai_documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_agent_runs (
    run_id TEXT PRIMARY KEY,
    document_id TEXT,
    session_id TEXT,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    input_payload TEXT DEFAULT '{}',
    output_payload TEXT DEFAULT '{}',
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(document_id) REFERENCES ai_documents(document_id) ON DELETE CASCADE
);

-- Legacy development tables
CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_sessions (
    session_id TEXT PRIMARY KEY,
    workspace_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    workspace_id TEXT,
    sha256 TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    total_pages INTEGER DEFAULT 0,
    total_characters INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    indexed INTEGER DEFAULT 0,
    mime_type TEXT DEFAULT 'application/pdf',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_documents (
    session_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY(session_id, document_id),
    FOREIGN KEY(session_id) REFERENCES research_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);
"""
