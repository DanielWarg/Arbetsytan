-- Initialize database schema for Arbetsytan

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    classification VARCHAR NOT NULL DEFAULT 'normal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_events (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    event_type VARCHAR NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actor VARCHAR,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_project_events_project_id ON project_events(project_id);
CREATE INDEX IF NOT EXISTS idx_project_events_timestamp ON project_events(timestamp DESC);

-- Add new columns to documents table (idempotent)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='documents' AND column_name='sanitize_level') THEN
        ALTER TABLE documents ADD COLUMN sanitize_level VARCHAR DEFAULT 'normal';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='documents' AND column_name='usage_restrictions') THEN
        ALTER TABLE documents ADD COLUMN usage_restrictions JSONB DEFAULT '{"ai_allowed": true, "export_allowed": true}';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='documents' AND column_name='pii_gate_reasons') THEN
        ALTER TABLE documents ADD COLUMN pii_gate_reasons JSONB;
    END IF;
END $$;

