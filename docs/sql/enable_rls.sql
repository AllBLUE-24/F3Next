-- Phase 2: Enable Row-Level Security (Supabase SQL Editor)
--
-- ⚠️ BEFORE RUNNING: Confirm DATABASE_URL uses the service_role connection
-- (its JWT password is longer than the anon JWT). If you're using the anon key
-- server-side, enabling RLS will return 0 rows for all queries and break the app.

-- Step 1: Enable RLS on all application tables
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE hooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE os_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE os_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE os_clarifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE context_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE context_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_company_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_target_structures ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_data_readiness_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_field_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_mapped_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_validation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_validation_errors ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_import_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_import_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_audit_trail ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_supervisor_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_file_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE is_f3iche_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE f3iche_definitions ENABLE ROW LEVEL SECURITY;

-- Step 2: Grant service_role full access to all tables
DO $$
DECLARE
    t text;
    tables text[] := ARRAY[
        'clients', 'projects', 'project_members', 'team_invites', 'hooks',
        'os_sessions', 'os_commands', 'os_clarifications',
        'context_snapshots', 'context_events',
        'is_sessions', 'is_company_profiles', 'is_target_structures',
        'is_data_readiness_assessments', 'is_field_mappings', 'is_mapped_data',
        'is_validation_results', 'is_validation_errors', 'is_import_plans',
        'is_import_logs', 'is_audit_trail', 'is_supervisor_prompts',
        'is_chat_messages', 'is_files', 'is_file_signals', 'is_f3iche_scores',
        'f3iche_definitions'
    ];
BEGIN
    FOREACH t IN ARRAY tables
    LOOP
        EXECUTE format(
            'DROP POLICY IF EXISTS "service_role_full_access" ON %I',
            t
        );
        EXECUTE format(
            'CREATE POLICY "service_role_full_access" ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)',
            t
        );
    END LOOP;
END $$;

-- Step 3: Block anon access (no anon policy = anon gets nothing)
-- If a future frontend uses Supabase Auth + anon key for row-scoped reads,
-- add per-table policies using auth.uid() at that time.
