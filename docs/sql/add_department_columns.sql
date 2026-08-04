-- Department columns for team routing (operations control plane Phase 0)
-- Run in Supabase SQL Editor (safe to re-run).
-- Replaces: alembic upgrade head

ALTER TABLE project_members
    ADD COLUMN IF NOT EXISTS department VARCHAR;

ALTER TABLE team_invites
    ADD COLUMN IF NOT EXISTS department VARCHAR;

CREATE INDEX IF NOT EXISTS idx_project_members_department
    ON project_members (project_id, department)
    WHERE department IS NOT NULL;
