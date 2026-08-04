# Database Optimization — Supabase Free Plan

> **Status:** Ready for review / implementation  
> **Author:** Antigravity audit — June 2026  
> **Scope:** Reduce Network Egress + Disk IOPS to stay within Supabase Free Plan limits

---

## Background & Architecture

F3Next connects to Supabase PostgreSQL via **SQLAlchemy `AsyncSessionLocal`** (asyncpg).  
There is **no `supabase-py` client** — all queries are ORM-based `select()` / `update()` / `insert()`.  
The key singleton is [`shared/database/db.py`](../shared/database/db.py) → `AsyncSessionLocal`.

Primary database-writing paths:
1. **Backend API** (`backend/app/api/`) — user-facing request handling
2. **IS Launchers** (`backend/app/services/is_launcher.py`) — state reading for IS workflow
3. **Container Activities** (`containers/*/activities.py`) — Temporal workflow nodes writing pipeline outputs
4. **CVS Poller / Recovery** (`containers/context_versioning/`) — background scheduled workers

---

## ✅ What's Already Well-Optimized

| Pattern | Where |
|---------|-------|
| All IS table indexes (`session_id`, `status`, etc.) | Declared in `shared/models/is_models.py` |
| CVS table indexes (`project_id`, `layer`, `version`) | Declared in `shared/models/cvs_models.py` |
| OS table indexes (`project`, `client`, `workflow_id`) | Declared in `shared/models/os_models.py` |
| `_get_session()` in is_launcher | `.limit(1)` ✓ |
| `get_supervisor_prompts()` | `.limit(50)` ✓ |
| `read_latest_snapshot()` in CVS | `.limit(1)` ✓ |
| `recover_stuck_events()` recovery worker | `.limit(50)` ✓ |
| `fetch_profile_from_db()` in OS company_profile | Raw SQL with `LIMIT 1` ✓ |
| OS session company-context cache | 5-min TTL in `os_sessions.company_context` ✓ |
| RAG / KB cache | In-memory + Redis TTL ✓ |

---

## 🔴 Root Causes of High Egress & Disk IO

### 1. N+1 Queries — Validation Report Loader (Highest Impact)

**Files:**
- [`backend/app/services/is_launcher.py`](../backend/app/services/is_launcher.py) — `get_validation_report()` L469–510, `get_validate_preview()` L807–826
- [`backend/app/services/is_chat_dispatcher.py`](../backend/app/services/is_chat_dispatcher.py) — `build_session_context()` L111–135

**Current pattern:**
```python
# 1 query for all ISValidationResult rows (no limit)
results = await session.execute(select(ISValidationResult).where(session_id == ...))

for vr in results:                                          # For each result (5–15 rows)…
    errors = await session.execute(
        select(ISValidationError).where(validation_result_id == vr.id)  # N extra queries
    )
    md = await session.execute(
        select(ISMappedData).where(id == vr.mapped_data_id)             # N more queries
    )
```

**Impact:** 10 doctypes → **1 + 10 + 10 = 21 DB queries** per status call.

**Fix — batch load:**
```python
# One query for all results (with limit)
vr_rows = (await session.execute(
    select(ISValidationResult)
    .where(ISValidationResult.session_id == session_id)
    .limit(50)
)).scalars().all()

# One query for ALL errors in one shot
vr_ids = [vr.id for vr in vr_rows]
err_rows = (await session.execute(
    select(ISValidationError)
    .where(ISValidationError.validation_result_id.in_(vr_ids))
    .limit(500)
)).scalars().all()

# Group in Python — zero extra DB round-trips
errors_by_vr_id: dict = {}
for e in err_rows:
    errors_by_vr_id.setdefault(e.validation_result_id, []).append(e)
```

---

### 2. Unbounded `.scalars().all()` Without `.limit()`

| File | Line(s) | Query | Fix |
|------|---------|-------|-----|
| `is_launcher.py` | L807–813 | `select(ISMappedData).where(session_id==...)` | `.limit(100)` |
| `is_launcher.py` | L816–819 | `select(ISValidationResult).where(session_id==...)` | `.limit(50)` |
| `is_launcher.py` | L736–742 | `select(ISImportLog).where(import_plan_id==...)` | `.limit(200)` |
| `is_chat_dispatcher.py` | L111–117 | `select(ISValidationResult).where(session_id==...)` | `.limit(50)` |
| `validation_agent/activities.py` | L492 | `select(ISMappedData).where(session_id==...)` | `.limit(100)` |
| `import_agent/activities.py` | L1028 | `select(ISMappedData).where(session_id==...)` | `.limit(100)` |
| `import_agent/activities.py` | L1043 | `select(ISValidationResult).where(session_id==...)` | `.limit(50)` |
| `import_agent/activities.py` | L1325 | `select(ISValidationResult).where(session_id==...)` | `.limit(50)` |
| `mapping_agent/activities.py` | L1465 | `select(ISFieldMapping).where(session_id==...)` | `.limit(500)` |
| `mapping_agent/activities.py` | L1548 | `select(ISFieldMapping).where(...)` | Narrow to 2 columns + `.limit(500)` |

---

### 3. CVS Status Endpoint — 3 Queries Per Request Instead of 1

**File:** [`backend/app/api/cvs.py`](../backend/app/api/cvs.py) — L303–314

**Current:**
```python
for layer in ["identity", "master_data", "transaction_intel"]:
    result = await session.execute(
        select(ContextSnapshot)
        .where(project_id == ..., layer == layer)
        .order_by(version.desc())
        .limit(1)
    )
```

**Fix — single query with `DISTINCT ON`:**
```python
from sqlalchemy import text

rows = (await session.execute(
    text("""
        SELECT DISTINCT ON (layer) layer, version, data, created_at
        FROM context_snapshots
        WHERE project_id = :pid
        ORDER BY layer, version DESC
    """),
    {"pid": project_id_uuid},
)).mappings().all()

snapshots = {row["layer"]: row for row in rows}
```

---

### 4. `invalidate_session_cache` — Loads Full JSONB Objects Unnecessarily

**File:** [`containers/context_versioning/context_store/activities.py`](../containers/context_versioning/context_store/activities.py) — L107–121

**Current (❌ wrong):** Loads full `OSSession` objects (including `company_context` JSONB blob, `session_context` JSONB array) just to set one field to `null`.

```python
result = await session.execute(select(OSSession).where(project_id==..., status=='active'))
sessions = result.scalars().all()
for s in sessions:
    s.company_context = None
await session.commit()
```

**Fix — targeted `UPDATE`, no `SELECT`:**
```python
from sqlalchemy import update
from sqlalchemy.sql import func as sqlfunc

result = await session.execute(
    update(OSSession)
    .where(OSSession.project_id == project_id, OSSession.status == "active")
    .values(company_context=None)
    .returning(OSSession.id)
)
count = len(result.fetchall())
await session.commit()
```

---

## 🟡 Missing Database Indexes (Only 2 Genuinely Missing)

All major IS / CVS / OS indexes are already declared in the Python models. The only missing ones:

| Table | Column | Why Needed |
|-------|--------|-----------|
| `hooks` | `project_id` | FK exists but no `Index()` declared in `hooks.py`; all hook lookups filter by `project_id` |
| `projects` | Partial index on `deployment_details IS NOT NULL` | CVS poller scans this on every cycle |

### SQL — run in Supabase SQL Editor

```sql
-- Missing: hooks.project_id index
CREATE INDEX IF NOT EXISTS idx_hooks_project_id
    ON hooks (project_id);

-- Missing: partial index for CVS poller (only deployed projects)
CREATE INDEX IF NOT EXISTS idx_projects_deployed
    ON projects (id, company_slug)
    WHERE deployment_details IS NOT NULL;
```

---

## 🔒 Row-Level Security (RLS)

Supabase's `anon` role currently has unrestricted access to all tables. RLS must be enabled.

> **⚠️ BEFORE RUNNING**: Confirm that `DATABASE_URL` in `.env` uses the **`service_role`** connection  
> (its JWT password is longer than the `anon` JWT). If you're using the `anon` key server-side,  
> enabling RLS will immediately return 0 rows for all queries and break the app.

### SQL — run in Supabase SQL Editor (after confirming service_role key)

```sql
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
-- (service_role bypasses RLS by default in Supabase, but this policy
--  ensures access is explicit and auditable)
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
            'CREATE POLICY "service_role_full_access" ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)',
            t
        );
    END LOOP;
END $$;

-- Step 3: Block anon access (no anon policy = anon gets nothing)
-- If a future frontend uses Supabase Auth + anon key for row-scoped reads,
-- add per-table policies using auth.uid() at that time.
```

---

## 📋 Implementation Checklist

### Phase 1 — Code Changes (no deployment risk)
- [x] `is_launcher.py` → fix N+1 in `get_validation_report()` + `get_validate_preview()`; add limits
- [x] `is_chat_dispatcher.py` → fix N+1 in `build_session_context()`; add `.limit(50)`
- [x] `context_store/activities.py` → replace SELECT+loop with single UPDATE in `invalidate_session_cache()`
- [x] `cvs.py` → replace 3-query layer loop with single `DISTINCT ON` query
- [x] `validation_agent/activities.py` → add `.limit(100)` to `ISMappedData` fetch
- [x] `import_agent/activities.py` → add limits at L1028, L1043, L1325
- [x] `mapping_agent/activities.py` → add limits + column narrowing at L1465, L1548

### Phase 2 — SQL (run in Supabase SQL Editor or `python scripts/apply_db_optimization.py`)
- [x] Run [`docs/sql/add_missing_indexes.sql`](sql/add_missing_indexes.sql) (2 indexes: `hooks.project_id`, `projects` partial)
- [x] Confirm `DATABASE_URL` uses `service_role` key (script checks JWT role + `rolbypassrls`)
- [x] Run [`docs/sql/enable_rls.sql`](sql/enable_rls.sql) (idempotent; skipped automatically if anon key detected)
- [x] Verify table reads after RLS (`apply_db_optimization.py` post-check)

### Phase 3 — Optional Tuning
- [x] Increase `CVS_POLL_INTERVAL_SEC` default from `900` (15 min) to `1800` (30 min) — halves CVS poller IOPS
- [x] Set `CONTEXT_ENGINE_L1_TTL` default to `600` (10 min instead of 5) to reduce cache misses
- [x] Document `REDIS_URL` in `.env.example`; wire into `cvs_poller` in `docker-compose.yml`

### Phase 4 — CVS Data Lifecycle (Foundation L0 baseline)

**Problem:** `context_snapshots` stores a full JSONB copy on every CVS sync trigger (webhook, poller, OS command). The app only reads `ORDER BY version DESC LIMIT 1`, but historical rows were never deleted — causing multi-GB Supabase bloat. Full payloads are already duplicated in **R2** (`r2_key` on each retained row).

**Retention policy (Option 3):**

| Table | Supabase retention | Long-term archive |
|-------|-------------------|-------------------|
| `context_snapshots` | Latest version per `(project_id, layer)` only | R2 versioned keys |
| `context_events` | Last 30 days (audit / recovery) | None |

**Automated enforcement:**

| Mechanism | When | Scope |
|-----------|------|-------|
| `prune_old_snapshots` activity | After every successful `CVSUpdateWorkflow` write (Step 2c) | Per `project_id` |
| `cvs_prune` worker (`prune_worker.py`) | Daily (`CVS_PRUNE_INTERVAL_SEC=86400`) | Global + `VACUUM FULL` |

**Env vars:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `CVS_EVENTS_RETENTION_DAYS` | `30` | Delete `context_events` older than N days |
| `CVS_PRUNE_INTERVAL_SEC` | `86400` | Daily prune worker interval |

**Emergency one-shot cleanup** (Supabase SQL Editor or script):

```bash
python scripts/prune_cvs_storage.py
python scripts/reclaim_supabase_storage.py --apply --yes
```

See [`SUPABASE_STORAGE_PLAN.md`](SUPABASE_STORAGE_PLAN.md) for the billing-period plan (CVS tables only).

Or run [`docs/sql/prune_cvs_storage.sql`](sql/prune_cvs_storage.sql) or [`docs/sql/reclaim_supabase_storage.sql`](sql/reclaim_supabase_storage.sql) manually, then verify row counts drop to ~`(projects × layers)` for snapshots.

**Implementation checklist:**

- [x] `prune_old_snapshots` + `prune_old_snapshots_core` in `context_store/activities.py`
- [x] CVS workflow Step 2c — post-write per-project prune
- [x] `prune_worker.py` + `cvs_prune` service in `docker-compose.yml`
- [x] `scripts/prune_cvs_storage.py` + `docs/sql/prune_cvs_storage.sql`

---

## Estimated Impact

| Optimization | Estimated Query Reduction |
|-------------|--------------------------|
| Fix N+1 in validation report | ~80% fewer queries per IS status call |
| Add limits to unbounded queries | Caps egress at bounded worst-case |
| CVS status endpoint (3→1 query) | 66% fewer queries on `/cvs/status` |
| `invalidate_session_cache` UPDATE | Eliminates JSONB blob read per invalidation |
| Missing indexes | Prevents full-table scans on `hooks` + `projects` |
| Doubling CVS poll interval | ~50% reduction in CVS background IO |
| CVS snapshot retention (Option 3) | Caps `context_snapshots` at ~N rows (projects × layers); prevents GB-scale JSONB bloat |
| Daily `VACUUM FULL` via `cvs_prune` | Reclaims physical disk after deletes on Supabase |

These changes together should bring the project well within the **5 GB/month egress**, **0.5 GB disk**, and **Disk IO budget** limits of the Supabase Free Plan.
