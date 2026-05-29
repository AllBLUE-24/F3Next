# Green Surface Beta Report

> **Date:** 2026-05-26  
> **Corpus:** 8-file Green Surface golden matrix  
> **Reference project:** `2d21a137-c8b1-4845-b0be-c8adb9a2e967` (strahats)  
> **Status:** Classified failures logged — beta success per PRIORITIES (3–5 understood failures)

---

## Summary

| Metric | Result |
|--------|--------|
| Validate loop | Shipped (Tier 1 honesty) |
| Import plan finalize | `ready_with_gaps` after worker fix (harness verified) |
| Live import (partial) | ~8/40 records succeeded |
| Workflow stage honesty | **Fixed** — was `complete` on errors; now `complete_with_errors` |
| Prerequisite order | **Fixed** — setup wizard on greenfield; skip baseline catalog when Company exists |

---

## Classified failures (A/B/C/D)

| # | Symptom | Class | Layer | Pillar | Root cause | Fix status |
|---|---------|-------|-------|--------|------------|------------|
| 1 | Company create failed on fresh site (missing Transit warehouse type) | A | L4 | 10 | `ensure_site_prerequisites` ran before baseline seed | **Fixed** — `_run_baseline_preflight_seed` before prerequisites |
| 2 | UI showed "Import complete" when BOM/WO/PR/Stock Entry failed | A | L1 | 9 | Workflow ignored `steps_failed > 0` | **Fixed** — `complete_with_errors` stage |
| 3 | Import UI hid per-doctype failure counts | A | L5 | 9 | ImportView not wired to import-results API | **Fixed** |
| 4 | `05_gs_active_projects.csv` classified as Purchase Receipt | B + D | L2/L0 | 3 | LLM degraded (`proxies` / missing openai in worker) | **Partial** — OS deps pinned; live worker rebuild pending |
| 5 | BOM 0/2, Stock Entry 0/8, WO 0/2, PR 0/12, Project 0/2 | B + C | L3/L4 | 5, 10 | Link resolution + lifecycle deps; transactional phase needs masters + submitted BOMs | Tier 7 / golden re-run after deploy |
| 6 | Stale blocked import plan after worker rebuild | A | L2 | 8 | DB plan not auto-refreshed on code deploy | **Fixed** — `POST /api/implementation/re-finalize-plan/{project_id}` |
| 7 | OS "create customer" broken | D | L0 | — | Shared LLM import failure in OS worker | **Partial** — deps aligned; smoke script added |

---

## Golden run checklist (next deploy)

1. Rebuild IS + OS workers with updated `requirements.txt`
2. Run `python -m shared.smoke_llm` on worker host
3. Fresh session — upload all 8 Green Surface files
4. Validate against [`GREEN_SURFACE_GOLDEN_MATRIX.md`](../containers/implementation/dev_fixtures/GREEN_SURFACE_GOLDEN_MATRIX.md)
5. `POST /api/implementation/re-finalize-plan/{project_id}` if reusing session after worker update
6. Approve live import; confirm UI shows import-results per doctype
7. Expect `complete` or honest `complete_with_errors`

---

## Next work (post-closure)

- Tier 3: chat bar on Validate
- Tier 3: classification transparency
- Tier 7 (one item): wire `validation_rules.json` OR SchemaResolver v1
- Full golden re-run as gate after worker deploy
