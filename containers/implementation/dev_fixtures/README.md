# IS Dev Fixtures

These JSON files are the input fixtures for `is_harness.py`.
Each file corresponds to one IS activity step and contains the minimum input needed to run it in isolation.

## Quick Start

```bash
# From the repo root:

# 1. Test the import plan builder (pure DB read, no LLM):
python -m containers.implementation.is_harness --step build_import_plan

# 2. Dry-run Phase A without touching ERPNext:
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_a_config --dry-run

# 3. Test target structure without spending Gemini tokens:
python -m containers.implementation.is_harness --step build_target_structure --mock-llm

# 4. Run file mapping on a real session:
python -m containers.implementation.is_harness --step map_file_to_erpnext

# 5. Save result to a file instead of stdout:
python -m containers.implementation.is_harness --step build_import_plan --output /tmp/plan.json
```

## How to Fill In `session_id` and `project_id`

Most steps need a real `session_id` (UUID) from the `is_sessions` table in Supabase.
The easiest way to get one is to run the workflow through at least step 0 (session creation)
once, then copy the UUID from Supabase:

```sql
-- Run in Supabase SQL editor:
SELECT id, project_id, status, created_at
FROM is_sessions
ORDER BY created_at DESC
LIMIT 5;
```

Copy the `id` into `session_id` and the `project_id` column into `project_id` in your fixture.

## Steps That Need Real Data vs Pure Fixtures

| Step | Needs DB? | Needs R2? | Needs ERPNext? | Needs LLM? |
|---|---|---|---|---|
| `build_import_plan` | ✅ | ❌ | ❌ | ❌ |
| `execute_import_phase` | ✅ | ✅ | ✅ (unless `dry_run=true`) | ❌ |
| `build_target_structure` | ✅ | ✅ | ❌ | ✅ (`--mock-llm` to skip) |
| `validate_mapped_data` | ✅ | ✅ | ❌ | ❌ |
| `map_file_to_erpnext` | ✅ | ✅ | ❌ | ✅ (`--mock-llm` to skip) |
| `infer_f3iche` | ✅ | ✅ | ❌ | ✅ (`--mock-llm` to skip) |
| `verify_f3iche` | ✅ | ❌ | ❌ | ❌ |
| `build_company_profile` | ✅ | ✅ | ❌ | ✅ (`--mock-llm` to skip) |
| `virus_scan_quarantine` | ✅ | ✅ | ❌ | ❌ |
| `fetch_clean_files` | ❌ | ✅ | ❌ | ❌ |

## Notes

- The harness runs **outside Temporal**. No worker or Docker needed.
- All activity logs are printed to the terminal exactly as they would appear in the worker.
- `--mock-llm` stubs out `generate_json` and the key pool so no Gemini API calls are made.
- `--dry-run` on `execute_import_phase` reads the plan and logs each row but does NOT POST to ERPNext.
- Use `--output <file>` to save the result JSON for further inspection.
