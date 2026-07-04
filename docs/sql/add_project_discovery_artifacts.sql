-- Discovery artifacts: project_target_structures + project_mvp_boundaries
-- Run in Supabase SQL Editor (safe to re-run).
-- Replaces: alembic upgrade head

-- ── Tables (if not created yet) ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_target_structures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    f3iche VARCHAR NOT NULL,
    discovery_bottleneck TEXT,
    llm_enhanced BOOLEAN DEFAULT false,
    llm_reasoning TEXT,
    total_doctypes INTEGER,
    total_seed_doctypes INTEGER,
    total_setup_steps INTEGER,
    r2_target_path VARCHAR,
    r2_mvp_path VARCHAR,
    seed_doctypes JSONB,
    required_doctypes JSONB,
    setup_steps JSONB,
    import_phases JSONB,
    validation_rules JSONB,
    mvp_focus JSONB,
    deferred_doctypes JSONB,
    corpus_independent BOOLEAN DEFAULT true,
    graph_driven BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_project_target_structures_project_id
    ON project_target_structures (project_id);

CREATE TABLE IF NOT EXISTS project_mvp_boundaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    f3iche VARCHAR NOT NULL,
    primary_bottleneck TEXT,
    functional_requirements JSONB,
    seed_doctypes JSONB,
    deferred_doctypes JSONB,
    mode VARCHAR NOT NULL DEFAULT 'f3iche_template',
    llm_enhanced BOOLEAN DEFAULT false,
    llm_reasoning TEXT,
    r2_path VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_project_mvp_boundaries_project_id
    ON project_mvp_boundaries (project_id);

-- ── Consolidated JSON columns (same row, separate blobs) ─────────────────────

ALTER TABLE project_target_structures
    ADD COLUMN IF NOT EXISTS target_structure_json JSONB;

ALTER TABLE project_target_structures
    ADD COLUMN IF NOT EXISTS mvp_boundary_json JSONB;

-- Verify (optional):
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'project_target_structures'
--   AND column_name IN ('target_structure_json', 'mvp_boundary_json');
