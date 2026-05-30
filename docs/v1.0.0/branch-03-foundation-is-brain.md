# Branch 03 — `foundation/is-brain`

> **Base:** `foundation/os-brain` (or rebase on `main` after os-brain merge)  
> **Requires:** `foundation/shared-platform` merged (LER API stable)  
> **Layer focus:** L2–L4  
> **IS pillars:** 1–10 (corpus, mapping, validate, import, readiness)  
> **Class:** **A** + **C** (unify gates, prune duplicate paths)

---

## 1. Branch thesis

IS is the **long pole**: upload → classify → map → validate → import must use the **same four gates** and **LER authority** as OS. After this branch, data imported via IS is immediately operable via OS without “stale CVS” class failures, and readiness blockers reflect **live ERP** emptiness.

---

## 2. Current IS architecture (baseline)

Reference: [`ARCH_IMPLEMENTATION.md`](../ARCH_IMPLEMENTATION.md)

| Stage | Activities / modules | Gate today |
|-------|----------------------|------------|
| Upload | parse, virus scan, R2 | — |
| Classify | `infer_doctype`, LLM refine | partial RESOLVE |
| Map | `map_file_to_erpnext`, KB-04 | RESOLVE (columns) |
| Validate | validation agent, rules JSON | partial COMMIT read |
| Readiness | `assess_data_readiness`, supervisor | COMPLETE (fragmented) |
| Import | phased `execute_import_phase`, preflight | COMMIT |
| CVS sync | webhooks, force-sync step | freshness |

**Gap:** `BulkLinkResolver` in import preflight but not in validate/readiness/classify consistently; supervisor re-derives gaps differently than readiness agent.

---

## 3. Target IS gate mapping

| Gate | IS implementation (target) |
|------|----------------------------|
| **RESOLVE** | Classify files → map columns → **LER pass on mapped rows** → canonical link values in row dicts |
| **COMPLETE** | **Single** `assess_data_readiness` output = `complete_gaps` consumed by supervisor (no second scan) |
| **CLARIFY** | Supervisor questions + chat bar + re-upload → corpus merge → back to RESOLVE |
| **COMMIT** | Honest validate → import phases → `import-results` API |

---

## 4. File-level change plan

### 4.1 RESOLVE — link resolution on validate path

| File | Change |
|------|--------|
| [`containers/implementation/import_agent/preflight.py`](../../containers/implementation/import_agent/preflight.py) | Already uses `BulkLinkResolver` — refactor to `shared.entity_resolution.ler` |
| `containers/implementation/validation_agent/` | Before row rules: apply LER rewrite to mapped payloads (same as preflight) |
| `containers/implementation/mapping_agent/` | Emit `link_targets` metadata on mapped files for LER |
| New: `containers/implementation/entity_resolution/activities.py` | `resolve_mapped_links(project_id, file_id)` activity optional for workflow clarity |

**Behavior:** Validator errors “unknown link” only when LER cannot resolve **and** user did not clarify.

### 4.2 RESOLVE — classify + SchemaResolver bridge

| File | Change |
|------|--------|
| `containers/implementation/classification_agent/` | Wire SchemaResolver v1 where pillar 6 backlog specifies |
| [`shared/kb/schema_resolver.py`](../../shared/kb/schema_resolver.py) if exists | Single entry for doctype inference |

**Ideation:** Classify proposes doctype; RESOLVE confirms with LER sample rows (e.g. Item Code column matches live items).

### 4.3 COMPLETE — unified readiness

| File | Change |
|------|--------|
| `containers/implementation/readiness_agent/` | Returns `GateResult`-shaped `complete_gaps` |
| `containers/implementation/supervisor_agent/` | **Consumes** readiness gaps; does not re-implement industry rules |
| [`corpus_merge.py`](../../containers/implementation/corpus_merge.py) | Unchanged policy spine — readiness reads corpus state only |

**Prune:** Remove duplicate gap detection in supervisor that contradicts readiness (grep `required_master`, `missing_` patterns).

### 4.4 COMPLETE — live ERP emptiness

| Check | Old | New |
|-------|-----|-----|
| “No customers” blocker | CVS count = 0 | `list_records('Customer', limit=1)` empty when adapter up |
| Adapter down | Block with class D message | Same |

Files: readiness agent, `assess_data_readiness` helpers, deployment health check.

### 4.5 CLARIFY — supervisor + corpus loop

| File | Change |
|------|--------|
| `supervisor_agent` activities | Questions reference `GapItem.candidates` from LER |
| Re-upload handler | Union corpus → re-run RESOLVE only for affected files |
| Session store | Persist `gate_state` per wave (optional JSON column) |

### 4.6 COMMIT — honest validate & import

| File | Change |
|------|--------|
| `validation_agent` | `valid` / `partial` / `fail` enums → `HonestySlice` |
| `import_agent` phases | Per-phase errors surface in `import-results` |
| `ImplementationWorkflow` | Stage transitions: no `complete` if `steps_failed > 0` |

### 4.7 Freshness — align with OS brain

| Path | Change |
|------|--------|
| Webhook handler | Ensure `project_id` maps to CVS company_id |
| Post-import step (~13.5) | Force-sync documented in runbook; trigger after COMMIT success |
| `context_snapshots` for IS | Optional: store `link_cache` snapshot post-import for debugging |

### 4.8 Prune dead paths (ideation list)

Audit and remove or flag `deprecated`:

- Duplicate validate-only link checks that ignore LER rewrite  
- Filename-only doctype priors without KB promotion  
- Legacy mapping module paths superseded by KB-04  
- Supervisor branches that duplicate `validation_rules.json` logic  

**Rule:** Each removal needs harness step or golden matrix proof.

---

## 5. Workflow orchestration

**File:** `containers/implementation/implementation_workflow/workflow.py` (path may vary)

Suggested explicit gate checks:

```text
after mapping wave:
  resolve_mapped_links (LER)
  if resolution_gaps: supervisor CLARIFY
assess_data_readiness
  if complete_gaps: supervisor CLARIFY
validate (honest)
  if not valid: CLARIFY or fail
import phases (COMMIT)
finalize + CVS sync
```

Signals unchanged where possible — minimize frontend breakage until branch 05.

---

## 6. Shared module consumption

| Module | IS usage |
|--------|----------|
| `shared.entity_resolution` | Validate + import preflight + readiness live checks |
| `shared.gate_contracts` | Activity return types; API serialization |
| `shared.erp_semantics` | Row-level defaults mirroring OS (company, title where applicable) |
| `shared.erp_tools.list_master` | Supervisor candidate lists |

---

## 7. Intelligence (LLM) on IS

| Tier | Gate | Activity |
|------|------|----------|
| T1 | RESOLVE | classify, column infer |
| T2 | COMPLETE | supervisor copy, mapping refine |
| T0 | RESOLVE | LER bulk (no LLM for existence) |
| T3 | RESOLVE | ambiguous file understanding (existing refine paths) |

**Cost:** One LER `list_records` per doctype cheaper than failed import retry.

---

## 8. Tests & verification

| Suite | Command |
|-------|---------|
| Harness golden | Green Surface matrix steps |
| Unit | `containers/implementation/tests/test_ler_validate.py` (new) |
| Integration | Import preflight + validate same resolution_map |

**Golden rows:** `RELEASE_v1_0_0.md` G-IS-* ; cross-surface G-OS-SO-01 after IS import creates customer.

---

## 9. PR breakdown

1. Refactor preflight to `shared.entity_resolution`  
2. LER in validation agent  
3. Unified readiness → supervisor contract  
4. Live ERP emptiness checks  
5. Workflow gate ordering + honesty enums  
6. Prune pass (separate PR with harness proof)  
7. `ARCH_IMPLEMENTATION.md` gate diagram  

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Large blast radius | Feature flag `IS_USE_LER_VALIDATE=1` for pilot |
| Harness duration | Run subset per PR |
| SchemaResolver half-wired | Class C item — document in backlog if not done |

---

## 11. Success criteria

- [x] Unit: `containers/implementation/tests/test_ler_validate.py` + shared/OS suites  
- [x] Automated regression: `python scripts/verify_foundation.py`  
- [ ] G-IS-VAL-01, G-IS-IMP-01, G-IS-LER-01, G-IS-READ-01 pass (manual golden — [`FOUNDATION_VERIFICATION.md`](./FOUNDATION_VERIFICATION.md))  
- [ ] G-OS-SO-01 passes **without** manual CVS sync after IS import  
- [x] Supervisor consumes `gap_report.complete_gaps` from readiness (live ERP blockers)  
- [x] `ARCH_IMPLEMENTATION.md` gate diagram (Company Brain gates §)  
- **Deferred (branch 04+):** SchemaResolver wire, workflow reorder, honesty enum refactor, large supervisor prune  

---

*Next: [`branch-04-foundation-kb-validation.md`](./branch-04-foundation-kb-validation.md)*
