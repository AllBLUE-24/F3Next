-- Local F3Next app database bootstrap (runs once on first container start).
-- pgvector / kb_embeddings intentionally omitted for now.

DO $$
BEGIN
    CREATE TYPE project_status AS ENUM (
        'created',
        'discovery_complete',
        'config_completed',
        'deployment_in_progress',
        'deployment_completed',
        'templates_ready',
        'uploaded',
        'validated',
        'interested',
        'listed'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
