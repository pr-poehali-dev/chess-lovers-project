CREATE TABLE IF NOT EXISTS cloud_diagnostics (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    context_dir JSONB,
    context_attrs JSONB,
    raw_token TEXT,
    note TEXT
);