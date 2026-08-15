# Test Harness — Overview

Live end-to-end testing for F3Next's implementation pipeline. Cursor agents drive **real HTTP APIs** — the same routes the Next.js UI uses — not offline fixture UUIDs.

## Default mode: `live_e2e`

```text
Preflight (Docker + API)
     ↓
POST /api/onboarding/complete          → fresh project_id
     ↓
POST /api/discovery/chat … complete    → MVP boundary
POST /api/discovery/confirm-modules
POST /api/discovery/{id}/proceed-to-implementation
     ↓
POST /api/implementation/start
POST /api/implementation/upload-files
POST /api/implementation/signal/files-uploaded
     ↓
Poll stage + auto-respond to gates (f3iche, supervisor, readiness, mapping, validation)
     ↓
POST /api/implementation/signal/sandbox-approved (dry_run=true)
     ↓
Oracle validation + REVIEW.md report
```

Offline pytest / step harnesses are **optional regression shortcuts**, not the primary test.

## File structure

```
.skills/test-harness/
├── SKILL.md              ← Agent instructions (read this first)
├── API-REFERENCE.md      ← Endpoint cheat sheet
├── REVIEW-TEMPLATE.md    ← Report template agents fill in
├── config.json           ← URLs, timeouts, human_gates, preflight
├── examples/             ← Scenario definitions (expected outcomes)
│   └── project-chemical-wip.json
└── results/              ← Run artifacts (gitignored)
    └── test-run-YYYYMMDD-HHMMSS/
        ├── run_context.json
        ├── preflight.json
        ├── oracle_report.json
        ├── REVIEW.md
        ├── timeline.json
        ├── api/            ← Saved API responses
        └── corpus/         ← Generated upload files
```

## Prerequisites

| Service | Container | Required |
|---------|-----------|----------|
| FastAPI | `f3_backend_api` | Yes |
| IS worker | `f3_implementation_worker` | Yes |
| Temporal | `f3_temporal` | Yes |
| Postgres/Supabase | via `.env` | Yes |
| R2 | via `.env` | Yes (upload) |
| LLM | via `.env` | Yes (discovery + corpus) |
| ERPNext | staging | Only for live import (default: dry-run) |

Start stack:
```bash
docker compose up -d backend_api implementation_worker temporal temporal_db redis caddy
```

## Usage

```
/test-harness project-chemical-wip
/test-harness project-chemical-wip --implement-fixes
/test-harness --offline-regression    # pytest only — not E2E
```

## Oracles

Each stage compares **API response** vs **scenario expectations**:

| Stage | API | Validates |
|-------|-----|-----------|
| Discovery | `GET /discovery/{id}/blueprint-status` | Seed doctypes |
| Corpus | `GET /implementation/corpus-assignments/{id}` | File assignments |
| Readiness | `GET /implementation/readiness/{id}` | Gaps, viability |
| Map/Validate | `GET /implementation/map-validate/{id}` | import_ready |
| Import | `GET /implementation/import-results/{id}` | Phase outcomes |

## Human gates (auto-handled by agent)

The agent responds to supervisor/readiness/mapping/validation gates using scenario `gap_responses`. Import uses `dry_run: true` unless the user explicitly requests live ERPNext writes.

## Safety

- Fresh `test-harness-*` slugs per run — never touch production projects
- No live import without explicit approval
- Artifacts preserved on failure for debugging
- Code fixes require human approval (`--implement-fixes`)

## vs offline tests

| | Live E2E (this harness) | pytest / fixtures |
|--|-------------------------|-------------------|
| Creates project | Yes, via API | No |
| Runs discovery LLM | Yes | No |
| Runs Temporal workflow | Yes | No |
| Tests fail-closed gates | Yes | Partial |
| Speed | 5–20 min | ~1 min |
| Truth level | Production path | Logic regression |

Run **both**: pytest for fast regression, live E2E before merging pipeline changes.
