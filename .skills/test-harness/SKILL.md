# Test Harness — Live End-to-End Implementation Testing

## What this skill does

Runs **real** full-stack tests against F3Next's live API — same path the UI uses:

```text
Create project → Discovery chat → Confirm MVP → Upload corpus → Temporal workflow
→ Readiness / mapping / validation gates → Import (dry-run) → Review report
```

**Do not** default to offline fixtures or hardcoded GreenSurface session IDs. Those are regression shortcuts only.

## When to use

- Validate the implementation pipeline after code changes
- Test a F3iche archetype + pain pattern end-to-end
- Produce a review report with oracle diffs and layer diagnosis
- Debug where the pipeline blocks (readiness, mapping, import)

## How to invoke

```
/test-harness [scenario_name] [--implement-fixes] [--offline-regression]
```

**Examples:**
```
/test-harness project-chemical-wip
/test-harness project-chemical-wip --implement-fixes
/test-harness --offline-regression   # pytest only — NOT a substitute for E2E
```

---

## Agent role

You are a **live E2E test engineer**. Your job:

1. Preflight the stack (Docker + API)
2. Create a **fresh** test project via API (never reuse fixture UUIDs)
3. Drive discovery + implementation through **real HTTP endpoints**
4. Auto-respond to human gates using scenario `gap_responses`
5. Validate each stage with oracles (expected vs actual API payloads)
6. Write a **REVIEW.md** report (use `REVIEW-TEMPLATE.md`)
7. If `--implement-fixes`: diagnose, propose fixes, wait for human approval, apply, re-run

**Read first:** `config.json`, `API-REFERENCE.md`, scenario JSON in `examples/`.

---

## Phase 0: Preflight (required)

Before any test, verify live services. **Stop and report** if preflight fails — do not fall back to fixtures unless user explicitly asked for `--offline-regression`.

1. **Docker** — these containers must be running:
   - `f3_backend_api`
   - `f3_implementation_worker`
   - `f3_temporal`

   ```powershell
   docker ps --format "{{.Names}}"
   ```

   If missing and user allows: `docker compose up -d backend_api implementation_worker temporal temporal_db redis caddy`

2. **API base URL** — from `config.json`:
   - Primary: `http://localhost/api` (via Caddy)
   - Fallback: `http://127.0.0.1:8000/api` (direct uvicorn)

   Probe with `GET /api/onboarding/check-slug?type=company&slug=probe-<timestamp>`.

3. **Env** — confirm `.env` has DB, R2, LLM keys (read only; do not print secrets).

4. **Optional fast regression** — only if `config.optional_regression.run_pytest_before_e2e` is true:
   ```bash
   python -m pytest containers/implementation/tests/ -q --tb=short
   ```

Save preflight results to `results/test-run-<timestamp>/preflight.json`.

---

## Phase 1: Load scenario

Load `examples/{scenario_name}.json` (default: `project-chemical-wip`).

Key fields:
- `context` — company name, f3iche archetype
- `pain_point` — discovery chat opener
- `expected_mvp.seed_doctypes` — discovery oracle
- `corpus_files` — files to generate + expected doctype assignments
- `gap_responses` — answers for supervisor/readiness prompts
- `expected_record_counts` — import oracle (lenient if dry-run)

Create run directory: `results/test-run-<YYYYMMDD-HHMMSS>/`

---

## Phase 2: Create fresh test project (API)

**Never** insert directly into Supabase or reuse GreenSurface IDs.

1. Generate unique slugs:
   - `company_slug`: `test-harness-<scenario>-<timestamp>`
   - `user_slug`: `test-harness-user-<timestamp>`
   - `user_id`: new UUID v4

2. Check slugs available:
   ```
   GET /api/onboarding/check-slug?type=company&slug=...
   GET /api/onboarding/check-slug?type=user&slug=...
   ```

3. Create project:
   ```http
   POST /api/onboarding/complete
   {
     "user_id": "<uuid>",
     "email": "test-harness@f3next.local",
     "full_name": "Test Harness",
     "user_slug": "...",
     "role": "owner",
     "company_name": "<from scenario.context.name>",
     "company_slug": "..."
   }
   ```

4. Save `project_id`, `company_slug`, all IDs to `results/.../run_context.json`.

---

## Phase 3: Generate corpus files

For each entry in `scenario.corpus_files`:

1. Write CSV (or xlsx if needed) under `results/.../corpus/`
2. Use `required_columns`, `sample_row_count`, `field_coverage_percent`
3. Leave ~20% of optional fields blank to surface real gaps

Do **not** skip file generation — upload these via the API in Phase 5.

---

## Phase 4: Discovery (live API)

Drive discovery exactly like the product UI.

### 4a. Chat
```
POST /api/discovery/chat
{ "project_id": "<uuid>", "message": "<scenario.pain_point>" }
```

Continue chatting (follow-up messages about WIP, batches, visibility) until:
- `ready_for_recommendation: true`, or
- 2+ user turns completed

Save each response to `results/.../api/discovery_chat_<n>.json`.

### 4b. Complete discovery
```
POST /api/discovery/complete
{ "project_id": "<uuid>" }
```

### 4c. Clarification (if needed)
If `GET /api/discovery/<id>/recommendation` returns `clarifying_questions`:
```
POST /api/discovery/clarification
{ "project_id": "<uuid>", "answers": { "<q_id>": "<sensible answer>" } }
```

Use scenario context to answer (manufacturing, chemical, WIP tracking).

### 4d. Confirm modules
```
GET /api/discovery/<id>/workflow-preview
```

```
POST /api/discovery/confirm-modules
{
  "project_id": "<uuid>",
  "confirmed_doctypes": <scenario.expected_mvp.seed_doctypes>,
  "added_doctypes": [],
  "removed_doctypes": [],
  "notes": "test-harness auto-confirm"
}
```

### 4e. Proceed to implementation
```
POST /api/discovery/<id>/proceed-to-implementation
```

### 4f. Discovery oracle
```
GET /api/discovery/<id>/blueprint-status
```

Compare actual seed doctypes vs `expected_mvp.seed_doctypes`.

| Strictness | Pass condition |
|------------|----------------|
| strict | Exact set match |
| lenient | All expected seeds present (extras allowed) |

Record PASS/FAIL in oracle report. **Continue E2E even on discovery FAIL** — full pipeline data helps diagnosis.

---

## Phase 5: Implementation workflow (live API)

### 5a. Start workflow
```
POST /api/implementation/start/<project_id>
```

Wait until session exists (poll `GET /api/implementation/state/<project_id>`).

### 5b. Upload files
Use multipart upload (same as UI):
```
POST /api/implementation/upload-files
  project_id=<uuid>
  files=@results/.../corpus/items.csv
  files=@results/.../corpus/work_orders.csv
  ...
```

### 5c. Verify + signal
```
POST /api/implementation/verify-uploads
POST /api/implementation/signal/files-uploaded
```

Include `company_slug` and `user_note: "test-harness"`.

### 5d. Poll + auto-respond to gates

Loop until terminal stage or timeout (`config.timeouts.workflow_stage_seconds`):

```
GET /api/implementation/stage/<project_id>
GET /api/implementation/state/<project_id>
GET /api/implementation/supervisor-prompts/<project_id>
```

**When gates appear, respond automatically** (unless `config.human_gates` disables):

| Gate | Endpoint | Default action |
|------|----------|----------------|
| F3iche | `POST /signal/f3iche-confirmed` | `accepted: true`, f3iche from scenario |
| Supervisor prompt | `POST /supervisor-prompts/respond` | Match `gap_responses` |
| Readiness yellow | `POST /readiness/decisions` | `decision: "proceed"` or `"acknowledge_yellow"` |
| Mapping | `POST /signal/mapping-confirmed` | `approved: true` |
| Validation | `POST /signal/validation-submitted` | empty responses + note |
| Import | `POST /signal/sandbox-approved` | `dry_run: true` (unless user opts in to live) |

After gap-related uploads, call:
```
POST /api/implementation/readiness/reassess/<project_id>
```

Log every stage transition with timestamp in `results/.../timeline.json`.

If workflow stuck >5 min with no stage change:
1. Check `docker logs f3_implementation_worker --tail 100`
2. Try `POST /api/implementation/reset/<project_id>` once, then re-upload

---

## Phase 6: Oracles (validate via API responses)

Fetch final artifacts and compare to scenario. Save diffs to `oracle_report.json`.

| Stage | Endpoint | Validate |
|-------|----------|----------|
| Discovery | `GET /discovery/<id>/blueprint-status` | seed doctypes |
| Corpus | `GET /implementation/corpus-assignments/<id>` | file → doctype |
| Readiness | `GET /implementation/readiness/<id>` | level, blocking gaps |
| Map/Validate | `GET /implementation/map-validate/<id>` | `import_ready`, errors |
| Import | `GET /implementation/import-results/<id>` | phase outcomes |

**Report format:**
```
=== Oracle Report ===
✅ Discovery: PASS (3/3 seeds)
❌ Corpus: FAIL — items.csv → BOM (expected Item)
⏸️  Readiness: SKIPPED (prior stage failed)
...
First failure: Corpus (L2)
Overall: FAIL
```

---

## Phase 7: Write review report

Fill `REVIEW-TEMPLATE.md` → save as `results/.../REVIEW.md`.

Include:
- Executive verdict (PASS/FAIL/PARTIAL)
- Oracle table with expected vs actual
- Stage timeline
- Worker log excerpts if failed
- Layer classification (L0–L6 per `docs/FOUNDATIONS.md`)
- Proposed fix with file paths (Read/Grep the codebase — cite real lines)

Present **REVIEW.md summary to the user** at end of run.

---

## Phase 8: Diagnose + fix (if failed and `--implement-fixes`)

1. Classify failure layer:
   - Discovery → L0 (LLM) or L1 (boundary)
   - Corpus → L2
   - Readiness → L3
   - Mapping → L4
   - Validation → L5
   - Import → L6

2. Read affected code + `docs/plans/is-pipeline-coherence.md`

3. **Human approval gate** — ask user before editing code

4. Apply fixes (StrReplace/Write), add regression test, commit to feature branch

5. Re-run full E2E from Phase 2 (new project) — max `config.diagnostician.max_fix_iterations`

---

## Phase 9: Cleanup

Per `config.json`:
- `preserve_on_failure: true` — keep project + R2 artifacts for debugging
- `delete_test_projects: false` by default — user can delete `test-harness-*` slugs manually

Always save artifacts under `results/test-run-<timestamp>/`.

---

## What NOT to do

- ❌ Do not use GreenSurface fixture session IDs (`3145be35-...`)
- ❌ Do not run `is_harness.py` with stale fixtures as the primary E2E test
- ❌ Do not treat pytest-only runs as "implementation system tested"
- ❌ Do not skip preflight and silently fall back to offline mocks
- ❌ Do not POST live import (`dry_run: false`) without explicit user approval
- ❌ Do not print secrets from `.env`

## What you MAY do as shortcuts

- ✅ `--offline-regression` → pytest only (fast, not E2E)
- ✅ Step harness matrix (`harness_corpus --matrix`) after E2E fails, to isolate a step
- ✅ `GET /implementation/state` polling instead of DB queries

---

## Configuration

| Key | Purpose |
|-----|---------|
| `execution_mode` | Must be `live_e2e` for this skill |
| `environment.api_base_url` | Primary API base |
| `timeouts.*` | Stage and poll timeouts |
| `human_gates.*` | Auto-respond behavior |
| `oracle_strictness.*` | strict vs lenient per stage |
| `cleanup.*` | Artifact retention |

---

## Reference files

- `API-REFERENCE.md` — all endpoints with request bodies
- `REVIEW-TEMPLATE.md` — report structure
- `examples/*.json` — scenario definitions
- `docs/arch/IMPLEMENTATION.md` — pipeline architecture
- `docs/FOUNDATIONS.md` — layer model (L0–L6)

---

## Notes

- Discovery chat is **synchronous API** (no discovery worker required).
- Implementation requires **Temporal worker** processing `is-queue`.
- Import tests default to **`dry_run: true`** — no ERPNext writes unless user opts in.
- When LLM variance causes discovery seed mismatch, report as L0/L1 with diff — do not auto-relax expectations without user approval.
