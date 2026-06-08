-- Phase 2: Missing indexes for F3Next (Supabase SQL Editor)
-- Safe to re-run: uses IF NOT EXISTS

CREATE INDEX IF NOT EXISTS idx_hooks_project_id
    ON hooks (project_id);

CREATE INDEX IF NOT EXISTS idx_projects_deployed
    ON projects (id, company_slug)
    WHERE deployment_details IS NOT NULL;
