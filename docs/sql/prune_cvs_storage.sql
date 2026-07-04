-- Emergency CVS storage reclaim (run in Supabase SQL Editor).
-- Keeps only the latest snapshot per (project_id, layer); full history stays in R2.

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

COMMIT;

-- Delete old audit events in batches if a single DELETE times out:
-- DELETE FROM context_events WHERE received_at < NOW() - INTERVAL '30 days';

-- Reclaim physical disk (may take several minutes on large tables).
VACUUM FULL context_snapshots;
VACUUM FULL context_events;
