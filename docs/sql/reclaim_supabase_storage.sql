-- One-shot CVS storage reclaim (context_snapshots + context_events ONLY).
-- Does NOT touch hooks, team_invites, IS, OS, or kb_embeddings.
-- Run in Supabase SQL Editor. Full payloads remain in R2 (context_snapshots.r2_key).

-- ── 0. Inspect (run first) ─────────────────────────────────────────────────
-- SELECT pg_size_pretty(pg_database_size(current_database()));
-- SELECT relname, pg_size_pretty(pg_total_relation_size(relid)), n_live_tup
-- FROM pg_stat_user_tables WHERE schemaname = 'public'
-- ORDER BY pg_total_relation_size(relid) DESC LIMIT 15;

-- ── 1. context_snapshots: keep latest per (project_id, layer) ───────────────
BEGIN;
SET LOCAL statement_timeout = 0;

CREATE TEMP TABLE cvs_snapshots_keep AS
SELECT DISTINCT ON (project_id, layer) *
FROM context_snapshots
ORDER BY project_id, layer, version DESC;

TRUNCATE context_snapshots;

INSERT INTO context_snapshots (
    id, project_id, layer, version, data, trigger_event,
    trigger_doctype, r2_key, created_at
)
SELECT
    id, project_id, layer, version, data, trigger_event,
    trigger_doctype, r2_key, created_at
FROM cvs_snapshots_keep;

UPDATE context_snapshots
SET data = jsonb_build_object(
    '_payload_in_r2', true,
    'counts', COALESCE(data->'counts', '{}'::jsonb)
)
WHERE r2_key IS NOT NULL
  AND NOT COALESCE((data->>'_payload_in_r2')::boolean, false);

COMMIT;

-- ── 2. context_events: 30-day audit window ──────────────────────────────────
DELETE FROM context_events
WHERE received_at < NOW() - INTERVAL '30 days';

-- ── 3. Reclaim physical disk (CVS tables only) ─────────────────────────────
VACUUM FULL context_snapshots;
VACUUM FULL context_events;

-- Verify:
-- SELECT pg_size_pretty(pg_database_size(current_database()));
-- SELECT COUNT(*) FROM context_snapshots;
