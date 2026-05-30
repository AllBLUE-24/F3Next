# v1.0.0 — Release Criteria & Golden Matrix

> Exit gates for tagging **`v1.0.0-rc`** and promoting to production.  
> Program overview: [`PLATFORM_OVERVIEW.md`](./PLATFORM_OVERVIEW.md).

---

## 1. Release definition

**v1.0.0** is the first product version where a company in F3Next’s **listed industry catalog** can:

1. Complete IS onboarding (upload → honest validate → live import) without lying UI.  
2. Run OS natural-language commands (SO/PO and core masters) with **live ERP** link authority.  
3. Share one **Company Brain** (LER + CVS hints + context + honesty) across IS and OS.

**Not required for v1.0.0-rc:** V2 single-agent rewrite, non-ERPNext adapters, mic/daily briefing UI.

---

## 2. Pre-tag checklist (all must pass)

### 2.1 Platform & deploy

| # | Criterion | Verify |
|---|-----------|--------|
| P1 | `foundation/shared-platform` merged to `main` | `shared/entity_resolution/` exists; gate contracts importable |
| P2 | `foundation/os-brain` merged | `resolve_entities` in workflow; no KB/pathlib in `workflow.py` |
| P3 | `foundation/is-brain` merged | Import preflight + validate use LER; unified COMPLETE |
| P4 | `foundation/kb-validation` merged | `os_validation.json` + `validation_rules.json` aligned |
| P5 | `foundation/frontend-contracts` merged | No `complete` when `steps_failed > 0`; OS confirm UX documented |
| P6 | Workers rebuilt | `docker compose build os_worker implementation_worker && up -d` |
| P7 | L0 smoke | `python -m shared.smoke_llm` after any LLM change |
| P8 | Docs | `ARCH_OS.md`, `ARCH_IMPLEMENTATION.md`, `FOUNDATIONS.md` reference gates + LER |

### 2.2 Honesty (L1)

| # | Criterion | Verify |
|---|-----------|--------|
| H1 | IS validate returns pass / partial / fail | Harness + UI |
| H2 | Import results API matches phase reality | `GET .../import-results/{project_id}` |
| H3 | OS terminal never shows success on execute failure | Golden commands |
| H4 | Semantic confirm timeout behavior documented | User knows auto-proceed policy |

### 2.3 Brain (LER)

| # | Criterion | Verify |
|---|-----------|--------|
| B1 | UI-created Customer visible to next OS command | Golden G-UI-01 |
| B2 | Company slug never sent as Company link | Regww golden |
| B3 | Validator errors on missing **live** link, not stale CVS alone | Strahats golden |
| B4 | Clarity does not emit `confidence≥0.9` with 0 CVS + 0 live | Strahats golden |

### 2.4 Execution safety

| # | Criterion | Verify |
|---|-----------|--------|
| E1 | Subcontract PO preflight blocks or warns before POST | Golden G-PO-SUB |
| E2 | `title` autofill on PO/SO; user never prompted | Unit `test_business_fields` |
| E3 | Clarification merge preserves supplier/customer on PO/SO | Unit tests |

---

## 3. Golden matrix (v1.0.0)

Use tenants from production learnings plus Green Surface harness where applicable.

### 3.1 OS — Strahats (`strahats` slug)

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| G-OS-SO-01 | SO after UI-created customer | Create Customer in ERP UI; command “sales order for X, item Y qty 1” | RESOLVE finds live customer; no `unknown_customer` from CVS-only |
| G-OS-SO-02 | Delivery date only clarification | “5th june” for delivery | Entities preserved; only schedule field updated |
| G-OS-SO-03 | CONFIRM path | Full flow to confirm | `POST /api/os/confirm/{id}` reaches workflow; no silent 5-min auto without user awareness |
| G-OS-SO-04 | Zero match honesty | Unknown customer name | `needs_human` or clarification; not `ambiguities=0` + high confidence |

### 3.2 OS — Regww (`regww` slug)

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| G-OS-CO-01 | Company resolution | Command with profile company slug | Payload `company` = live Company `name`, not slug |
| G-OS-PO-01 | PO without title prompt | “PO for supplier S, item I” | `title` autofill `{party}-{item}`; execute succeeds if ERP rules pass |
| G-OS-PO-02 | Subcontract item | PO for subcontracted item without flags | Preflight error **before** execute; plain message |

### 3.3 OS — Cross-cutting

| ID | Scenario | Expected |
|----|----------|----------|
| G-OS-VAL-01 | Validation repair loop | Fixable field asks user; autofill fields skipped; **no workflow crash** |
| G-OS-MERGE-01 | User answers `title` in clarification | `merge_clarification_into_intent` applies; round 2 does not corrupt supplier |

### 3.4 IS — Green Surface + industry rows

| ID | Scenario | Expected |
|----|----------|----------|
| G-IS-VAL-01 | Harness validate step | Honest partial when rows fail rules |
| G-IS-IMP-01 | Phased import | `steps_failed` reflected in API + UI |
| G-IS-LER-01 | Mapped row with alias warehouse | BulkLinkResolver rewrites before POST |
| G-IS-READ-01 | Readiness with empty live list | Blocker cites live ERP, not CVS-only |

### 3.5 Freshness

| ID | Scenario | Expected |
|----|----------|----------|
| G-FRESH-01 | Webhook after ERP edit | CVS updates async; next command LER still correct |
| G-FRESH-02 | Post-import force-sync | IS step 13.5 / documented sync path runs |

---

## 4. Regression suite commands

```bash
# Full foundation (recommended)
python scripts/verify_foundation.py

# Shared + OS unit
pytest shared/tests containers/os/tests -q

# IS brain
pytest containers/implementation/tests/test_ler_validate.py containers/implementation/tests/test_live_erp_readiness.py -q

# L0 (if LLM touched)
python -m shared.smoke_llm

# Manual golden matrix
# See docs/v1.0.0/FOUNDATION_VERIFICATION.md
# See containers/implementation/dev_fixtures/GREEN_SURFACE_GOLDEN_MATRIX.md
```

---

## 5. Rollout plan

| Phase | Audience | Action |
|-------|----------|--------|
| **rc** | Internal + pilot tenants | Tag `v1.0.0-rc`; deploy foundation workers |
| **beta** | Listed industries on invite | Monitor golden IDs weekly |
| **ga** | All listed industries | Tag `v1.0.0`; update customer-facing version string |

**Rollback:** Revert worker images to pre-foundation tag; `main` branch revert PR if schema incompatible.

---

## 6. Backlog updates (before merge to main)

For each merged foundation branch, add or update a line in:

- [`docs/PRIORITIES.md`](../PRIORITIES.md) — max 5 active; close completed v1.0 items  
- [`docs/IS_V2_BACKLOG.md`](../IS_V2_BACKLOG.md) — pillar mapping for IS items  

Format example:

```text
[v1.0.0 / foundation/os-brain] P0: LER in OS validator — L4, pillar 7, class A — G-OS-SO-01
```

---

## 7. Known acceptable failures (document, don’t hide)

| Failure | Class | v1.0.0 stance |
|---------|-------|---------------|
| BOM `disabled` field 417 on list | D / adapter | Log warning; document in runbook |
| Ambiguous warehouse pick | B | User clarification via IS supervisor |
| ERP business rule (credit limit, etc.) | B | Honest COMMIT failure + format_result |

---

## 8. Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Engineering | | | All P*, H*, B*, E* |
| Product | | | Golden matrix UX |
| Ops | | | Worker deploy + smoke |

---

*Update golden IDs when new production incidents occur; promote to KB via class B path.*
