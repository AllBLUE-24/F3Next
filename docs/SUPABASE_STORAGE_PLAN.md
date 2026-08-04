# Supabase Storage Plan — Stay Within Free Plan (512 MB)

> **Symptom:** Supabase dashboard shows **Database Size Exceeded** (~2.2 GB vs 0.5 GB limit) → 402 on all requests.  
> **Root cause:** Unpruned `context_snapshots` JSONB history (full payloads duplicated from R2).

---

## What is safe to prune

| Table | Action | Why safe |
|-------|--------|----------|
| **`context_snapshots`** | Keep **latest row only** per `(project_id, layer)`; strip inline JSONB when `r2_key` set | App reads `ORDER BY version DESC LIMIT 1`. Full history is in **R2**. |
| **`context_events`** | Delete rows older than **30 days** | Audit/recovery window only; not used for app state |

## What is NOT touched by automated retention

**Never deleted by `cvs_prune` or reclaim scripts:**

- `hooks`, `team_invites`, `clients`, `projects`, `project_members`
- All IS tables (`is_sessions`, `is_validation_errors`, `is_field_mappings`, …)
- All OS tables (`os_commands`, `os_sessions`, …)
- `kb_embeddings` (static RAG index)
- Discovery artifacts (`project_target_structures`, …)

Manual cleanup of dev/test data remains opt-in via existing scripts (`reset_implementation.py`, `reset_discovery.py`) — run only when you explicitly want to wipe a project.

---

## Immediate fix (one-time reclaim on Supabase)

Your local Postgres (`localhost:5433`) is separate. Supabase stays blocked until you reclaim **on Supabase**.

### 1. Point `DATABASE_URL` at Supabase (service_role JWT)

```env
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<SERVICE_ROLE_JWT>@...pooler.supabase.com:6543/postgres
USE_SQLITE=false
```

### 2. Report (read-only — deletes nothing)

```powershell
python scripts/reclaim_supabase_storage.py --report
python scripts/table_row_counts.py
```

### 3. One-time CVS reclaim

```powershell
python scripts/reclaim_supabase_storage.py --apply --yes
```

Or run [`docs/sql/reclaim_supabase_storage.sql`](sql/reclaim_supabase_storage.sql) in Supabase SQL Editor.

**Target:** Database size ≤ **512 MB**. If still over after CVS prune, the remainder is likely **`kb_embeddings`** (static vectors) — not deleted by this script.

---

## Billing period plan (ongoing — CVS only)

| Mechanism | Schedule | Tables touched |
|-----------|----------|----------------|
| `prune_old_snapshots` activity | After each CVS write | `context_snapshots`, `context_events` (per project) |
| **`cvs_prune` worker** | Daily | Same + `VACUUM FULL` on those two tables |
| New snapshot writes | Continuous | Stubs only in Postgres when R2 has payload |

**Start the worker when back on Supabase:**

```powershell
docker compose up -d cvs_prune
```

**Env vars (CVS only):**

```env
CVS_PRUNE_INTERVAL_SEC=86400
CVS_EVENTS_RETENTION_DAYS=30
```

---

## Disk budget after CVS retention

| Component | Expected size |
|-----------|---------------|
| `context_snapshots` | ~5–20 MB (3 rows × N projects, stubs) |
| `context_events` | ~20–40 MB (30-day window) |
| `kb_embeddings` | ~200–350 MB (static — monitor separately) |
| App tables | Grows with usage; not auto-pruned |

---

## Verification

```powershell
python scripts/table_row_counts.py
python scripts/reclaim_supabase_storage.py --report
```

Sanity checks:

- `context_snapshots` row count ≈ **projects × 3 layers**
- No `context_events` older than 30 days
- `hooks`, `team_invites`, etc. — row counts unchanged after reclaim

---

## Related

- [`DB_OPTIMIZATION.md`](DB_OPTIMIZATION.md) — query/egress optimizations
- [`docs/sql/prune_cvs_storage.sql`](sql/prune_cvs_storage.sql) — CVS-only SQL (same scope)
