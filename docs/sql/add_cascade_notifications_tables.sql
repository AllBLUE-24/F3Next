-- Cascade events + in-app notifications (operations control plane Phase 1)
-- Run in Supabase SQL Editor (safe to re-run).
-- Replaces: alembic upgrade head

CREATE TABLE IF NOT EXISTS cascade_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    doctype VARCHAR NOT NULL,
    doc_name VARCHAR,
    trigger_event VARCHAR NOT NULL,
    event_payload JSONB,
    matched_rule_ids JSONB DEFAULT '[]'::jsonb,
    risk_tier VARCHAR DEFAULT 'low',
    workflow_id VARCHAR,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cascade_events_project_received
    ON cascade_events (project_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_cascade_events_doctype
    ON cascade_events (project_id, doctype, doc_name);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cascade_event_id UUID REFERENCES cascade_events(id) ON DELETE SET NULL,
    project_id UUID NOT NULL,
    recipient_client_id VARCHAR NOT NULL,
    department VARCHAR,
    channel VARCHAR NOT NULL DEFAULT 'in_app',
    title VARCHAR NOT NULL,
    body TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    risk_tier VARCHAR DEFAULT 'low',
    status VARCHAR NOT NULL DEFAULT 'pending',
    related_os_workflow_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient_unread
    ON notifications (recipient_client_id, status, created_at DESC)
    WHERE status IN ('pending', 'sent');

CREATE INDEX IF NOT EXISTS idx_notifications_project
    ON notifications (project_id, created_at DESC);
