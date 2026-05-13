# IS Dev Fixtures

These JSON files are the input fixtures for `is_harness.py`.
Each file corresponds to one IS activity step and contains the minimum input needed to run it in isolation — **no Temporal worker, no Docker, no signal chain**.

## 📌 GreenSurface Reference IDs (use these in fixtures)

```
project_id  : b6ff0b7f-a616-4179-8f68-deda9b3578af
session_id  : 3145be35-2991-48dd-b43e-e59df9e86f5c
company_slug: green-surface
f3iche      : manufacturing_project_chemical
```

## Quick Start

```bash
# From the repo root:

# 1. Test the import plan builder (pure DB read, no LLM):
python -m containers.implementation.is_harness --step build_import_plan

# 2. Dry-run Phase A without touching ERPNext:
python -m containers.implementation.is_harness --step execute_import_phase --phase phase_a_config --dry-run

# 3. Test target structure without spending tokens:
python -m containers.implementation.is_harness --step build_target_structure --mock-llm

# 4. Run file mapping on a real session:
python -m containers.implementation.is_harness --step map_file_to_erpnext

# 5. Test Step 8b — derive prerequisite records (no LLM):
python -m containers.implementation.is_harness --step derive_required_records

# 6. Test Supervisor Agent with a simulated partial validation result:
python -m containers.implementation.is_harness --step supervise_step --mock-llm

# 7. Test Step 8c — data readiness assessment:
python -m containers.implementation.is_harness --step assess_data_readiness --mock-llm

# 8. Apply the supervisor's auto_fix patches to R2 payloads:
python -m containers.implementation.is_harness --step apply_supervisor_actions

# 8. Save any result to a file instead of stdout:
python -m containers.implementation.is_harness --step build_import_plan --output output.json
```

## How to Find Real Session IDs

```sql
-- Run in Supabase SQL editor:
SELECT id, project_id, status, created_at
FROM is_sessions
ORDER BY created_at DESC
LIMIT 5;
```

Copy the `id` into `session_id` and the `project_id` column into `project_id` in your fixture.

## Steps That Need Real Data vs Pure Fixtures

| Step | Needs DB? | Needs R2? | Needs ERPNext? | Needs LLM? | Plan Step |
|---|---|---|---|---|---|
| `virus_scan_quarantine` | ✅ | ✅ | ❌ | ❌ | Step 1 |
| `fetch_clean_files` | ❌ | ✅ | ❌ | ❌ | Step 2 |
| `infer_f3iche` | ✅ | ✅ | ❌ | ✅ (`--mock-llm`) | Step 3 |
| `verify_f3iche` | ✅ | ❌ | ❌ | ❌ | Step 5 |
| `align_discovery_and_signals` | ✅ | ❌ | ❌ | ✅ (`--mock-llm`) | Step 6a |
| `build_company_profile` | ✅ | ✅ | ❌ | ✅ (`--mock-llm`) | Step 7 |
| `retrieve_industry_knowledge` | ✅ | ❌ | ❌ | ❌ | Step 7a |
| `enrich_company_profile` | ✅ | ✅ | ❌ | ✅ (`--mock-llm`) | Step 7b |
| `merge_company_profile` | ✅ | ✅ | ❌ | ❌ | Step 7c |
| `build_target_structure` | ✅ | ✅ | ❌ | ✅ (`--mock-llm`) | Step 8 |
| `derive_required_records` | ✅ | ✅ | ❌ | ❌ | **Step 8b (NEW)** |
| `supervise_step` | ❌ | ❌ | ❌ | ✅ (`--mock-llm`) | **Supervisor (NEW)** |
| `apply_supervisor_actions` | ❌ | ✅ | ❌ | ❌ | **Supervisor (NEW)** |
| `map_file_to_erpnext` | ✅ | ✅ | ❌ | ✅ (`--mock-llm`) | Step 9 |
| `refine_mapping_with_llm` | ✅ | ✅ | ❌ | ✅ (`--mock-llm`) | Step 10 |
| `validate_mapped_data` | ✅ | ✅ | ❌ | ❌ | Step 11 |
| `build_import_plan` | ✅ | ❌ | ❌ | ❌ | Step 12 |
| `execute_import_phase` | ✅ | ✅ | ✅ (unless `--dry-run`) | ❌ | Steps 13-14 |

## Notes

- The harness runs **outside Temporal**. No worker or Docker needed.
- All activity logs are printed to the terminal exactly as they would appear in the worker.
- `--mock-llm` stubs out `generate_json` so no OpenAI API calls are made.
- `--dry-run` on `execute_import_phase` reads the plan and logs each row but does NOT POST to ERPNext.
- `supervise_step` deserializes the `status` field from the fixture JSON into a `NodeStatusEnvelope` automatically.
- `apply_supervisor_actions` deserializes the `actions` array into `SupervisorAction` objects automatically.
- Use `--output <file>` to save the result JSON for further inspection.


