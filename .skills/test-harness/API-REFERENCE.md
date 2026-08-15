# Test Harness — API Reference

Base URL: read `config.json` → `environment.api_base_url` (default `http://localhost/api`).

All routes are under `/api`. Use `curl`, `Invoke-RestMethod` (PowerShell), or `httpx` from Shell.

---

## 0. Preflight

```bash
# Docker services (must be running)
docker ps --format "{{.Names}}" | findstr f3_backend_api
docker ps --format "{{.Names}}" | findstr f3_implementation_worker
docker ps --format "{{.Names}}" | findstr f3_temporal

# API reachable (try fallback if Caddy not up)
curl -s -o /dev/null -w "%{http_code}" http://localhost/api/onboarding/check-slug?type=company&slug=test-probe
```

Start stack if needed (from repo root):
```bash
docker compose up -d backend_api implementation_worker temporal temporal_db redis caddy
```

---

## 1. Create test project

```http
POST /api/onboarding/complete
Content-Type: application/json

{
  "user_id": "<uuid>",
  "email": "test-harness@f3next.local",
  "full_name": "Test Harness Bot",
  "user_slug": "test-harness-<timestamp>",
  "role": "owner",
  "company_name": "ChemTech Industries",
  "company_slug": "test-harness-chem-<timestamp>"
}
```

Response: `{ "project_id": "<uuid>", ... }` — save this as `PROJECT_ID`.

Check slug availability first:
```http
GET /api/onboarding/check-slug?type=company&slug=test-harness-chem-<timestamp>
GET /api/onboarding/check-slug?type=user&slug=test-harness-<timestamp>
```

---

## 2. Discovery (Step 1)

### Chat
```http
POST /api/discovery/chat
{ "project_id": "<uuid>", "message": "<pain_point from scenario>" }
```

Repeat until response has `ready_for_recommendation: true` (usually 2+ user turns).

### Finalize discovery
```http
POST /api/discovery/complete
{ "project_id": "<uuid>" }
```

### Poll recommendation
```http
GET /api/discovery/<project_id>/recommendation
```

If `status: "incomplete"` and `clarifying_questions` present:
```http
POST /api/discovery/clarification
{ "project_id": "<uuid>", "answers": { "<question_id>": "<answer>" } }
```

### Workflow preview + module confirmation
```http
GET /api/discovery/<project_id>/workflow-preview
```

```http
POST /api/discovery/confirm-modules
{
  "project_id": "<uuid>",
  "confirmed_doctypes": ["Work Order", "BOM", "Item"],
  "added_doctypes": [],
  "removed_doctypes": [],
  "notes": "test-harness auto-confirm"
}
```

### Proceed to implementation (persist target + MVP)
```http
POST /api/discovery/<project_id>/proceed-to-implementation
```

### Discovery oracle
```http
GET /api/discovery/<project_id>/blueprint-status
```

Compare `target.seed_doctypes` (or `mvp_boundary`) against scenario `expected_mvp.seed_doctypes`.

---

## 3. Implementation workflow (Steps 2–5)

### Start workflow
```http
POST /api/implementation/start/<project_id>
```

### Upload corpus (multipart)
```http
POST /api/implementation/upload-files
Content-Type: multipart/form-data

project_id=<uuid>
files=@items.csv
files=@work_orders.csv
```

Response: `{ "uploaded_files": [{ "file_name", "object_path" }, ...] }`

### Verify R2
```http
POST /api/implementation/verify-uploads
{ "project_id": "<uuid>", "uploaded_files": [...] }
```

### Signal workflow
```http
POST /api/implementation/signal/files-uploaded
{
  "project_id": "<uuid>",
  "uploaded_files": [...],
  "company_slug": "<company_slug>",
  "user_note": "test-harness upload"
}
```

---

## 4. Poll state + human gates

### Poll until terminal or blocked
```http
GET /api/implementation/stage/<project_id>
GET /api/implementation/state/<project_id>
GET /api/implementation/tasks/<project_id>
```

Poll every `config.timeouts.workflow_poll_seconds` until:
- stage is terminal (`complete`, `complete_with_errors`, `error`, `*_blocked`), or
- timeout exceeded.

### F3iche confirmation gate
```http
GET /api/implementation/f3iche/confirmation/<project_id>
```

```http
POST /api/implementation/signal/f3iche-confirmed
{
  "project_id": "<uuid>",
  "accepted": true,
  "f3iche_user": "manufacturing_project_chemical"
}
```

### Supervisor prompts (gaps, uploads, readiness)
```http
GET /api/implementation/supervisor-prompts/<project_id>
```

```http
POST /api/implementation/supervisor-prompts/respond
{
  "project_id": "<uuid>",
  "prompt_id": "<id>",
  "chosen_action_id": "<action>",
  "extra_data": {}
}
```

Use scenario `gap_responses` to pick values. Prefer `provide_value` actions over defer when testing MVP path.

### Readiness gate
```http
GET /api/implementation/readiness/<project_id>
GET /api/implementation/data-readiness/<project_id>
```

```http
POST /api/implementation/readiness/decisions
{ "project_id": "<uuid>", "decision": "proceed" }
```

Reassess after gap uploads:
```http
POST /api/implementation/readiness/reassess/<project_id>
```

### Mapping gate
```http
GET /api/implementation/map-validate/<project_id>
```

```http
POST /api/implementation/signal/mapping-confirmed
{ "project_id": "<uuid>", "approved": true }
```

### Validation gate
```http
GET /api/implementation/validation/<project_id>
GET /api/implementation/validate-preview/<project_id>
```

```http
POST /api/implementation/signal/validation-submitted
{
  "project_id": "<uuid>",
  "responses": {},
  "note": "test-harness auto-submit"
}
```

### Import execution (dry-run by default)
```http
GET /api/implementation/import-execution/<project_id>
GET /api/implementation/import-plan/<project_id>
```

```http
POST /api/implementation/signal/sandbox-approved
{
  "project_id": "<uuid>",
  "dry_run": true
}
```

Poll results:
```http
GET /api/implementation/import-results/<project_id>
```

---

## 5. Oracle endpoints (read-only validation)

| Stage | Endpoint | Key fields to compare |
|-------|----------|----------------------|
| Discovery | `GET /discovery/<id>/blueprint-status` | `target.seed_doctypes` |
| Corpus | `GET /implementation/corpus-assignments/<id>` | file → doctype map |
| Readiness | `GET /implementation/readiness/<id>` | `readiness_level`, gaps |
| Map/Validate | `GET /implementation/map-validate/<id>` | `import_ready`, errors |
| Import | `GET /implementation/import-results/<id>` | phase status, record counts |

---

## 6. Reset (if workflow stuck)

```http
POST /api/implementation/reset/<project_id>
```

Then re-upload and signal again.
