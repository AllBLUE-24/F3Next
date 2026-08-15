# Test Harness Review — {{scenario_name}}

**Run ID:** {{run_id}}  
**Project ID:** {{project_id}}  
**Company slug:** {{company_slug}}  
**Started:** {{started_at}}  
**Duration:** {{duration_seconds}}s  
**Mode:** live_e2e (real API + Temporal + Supabase + R2)

---

## Executive summary

| Verdict | {{PASS | FAIL | ERROR | PARTIAL}} |
|---------|---|
| First failure stage | {{stage or "none"}} |
| Layer | {{L0–L6 or "n/a"}} |
| Blocking issue | {{one sentence}} |

---

## Preflight

| Check | Status | Notes |
|-------|--------|-------|
| `f3_backend_api` | | |
| `f3_implementation_worker` | | |
| `f3_temporal` | | |
| API reachable | | |
| R2 configured | | |
| LLM keys present | | |

---

## Oracle results

### Discovery
- **Expected seeds:** {{from scenario}}
- **Actual seeds:** {{from blueprint-status}}
- **Verdict:** PASS / FAIL
- **Diff:** 

### Corpus
- **Expected assignments:** {{from scenario}}
- **Actual assignments:** {{from corpus-assignments}}
- **Verdict:** PASS / FAIL
- **Diff:** 

### Readiness
- **Expected viability:** {{scenario or inferred}}
- **Actual:** `minimum_viable_import_possible`, `readiness_level`, blocking gap count
- **Verdict:** PASS / FAIL / LENIENT PASS
- **Diff:** 

### Mapping & validation
- **Expected:** import_ready, error count
- **Actual:** {{from map-validate}}
- **Verdict:** PASS / FAIL

### Import
- **Mode:** dry_run / live
- **Expected record counts:** {{from scenario}}
- **Actual:** {{from import-results}}
- **Verdict:** PASS / FAIL / SKIPPED

---

## Timeline (stage transitions)

| Time | Stage | Action taken |
|------|-------|--------------|
| | discovery/chat | |
| | discovery/complete | |
| | confirm-modules | |
| | proceed-to-implementation | |
| | implementation/start | |
| | files-uploaded | |
| | f3iche-confirmed | |
| | readiness | |
| | mapping-confirmed | |
| | validation-submitted | |
| | sandbox-approved | |

---

## Human gates auto-handled

List each supervisor prompt and how it was answered (from scenario `gap_responses`).

---

## Diagnostic report (if failed)

### Root cause
{{Plain language — what broke and why}}

### Layer classification
- **Layer:** L0 / L1 / L2 / L3 / L4 / L5 / L6
- **Fix type:** structural / kb_promotion / prompt_refinement / patch

### Evidence
- API response snippet or stage at failure
- Relevant log lines (`docker logs f3_implementation_worker --tail 100`)
- Code paths to inspect

### Proposed fix
1. 
2. 

### Regression test to add
- 

---

## Artifacts saved

- `results/{{run_id}}/scenario.json`
- `results/{{run_id}}/oracle_report.json`
- `results/{{run_id}}/api/` (key responses)
- `results/{{run_id}}/corpus/` (generated files)
- `results/{{run_id}}/REVIEW.md` (this file)

---

## Recommended next action

- [ ] User review only — no code change
- [ ] Approve fix implementation (`--implement-fixes`)
- [ ] Re-run after fixing environment
- [ ] Update scenario expectations (product behavior changed)
