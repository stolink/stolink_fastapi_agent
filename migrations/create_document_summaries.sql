-- Phase 3, 4를 위한 document_summaries 테이블 생성
CREATE TABLE IF NOT EXISTS document_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    document_id UUID NOT NULL,
    project_id UUID NOT NULL,
    level INT NOT NULL DEFAULT 3,
    summary TEXT NOT NULL,
    key_characters TEXT [] DEFAULT '{}',
    key_events TEXT [] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (document_id, level)
);

CREATE INDEX IF NOT EXISTS idx_summaries_project_level ON document_summaries (project_id, level);