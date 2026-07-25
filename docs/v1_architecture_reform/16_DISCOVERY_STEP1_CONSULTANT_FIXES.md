# Discovery Step 1 — Senior Consultant Review Fixes

> **Created**: 2026-07-25  
> **Status**: Active — engineering in progress  
> **Parent**: [`15_DISCOVERY_STEP1_V95_GATE.md`](./15_DISCOVERY_STEP1_V95_GATE.md)  
> **Source**: External senior ERPNext consultant end-to-end review

---

## Symptom (user terms)

Step 1 architecture is directionally correct (plan → validate → explain + closure test), but the **deliverables a consultant would sign** are broken or hollow: setup order is wrong, non-manufacturing niches get silent template substitution, rich F3iche playbook content is unused, and degraded planner paths can still show GREEN.

---

## Architecture triage

| Field | Value |
|-------|-------|
| **Layer** | L2 Discovery → L3 Target structure → L1 Honesty |
| **IS pillar** | Pillar 2 — Project target / MVP boundary |
| **Classification** | **A** code bugs (F1, F2, F6) + **B** KB wiring gaps (F3, F4) + **C** coverage extension (F5, F7) |

---

## Sprint plan

### Phase A — Trust the contract (P0)

| ID | Fix | Class | Files | Verification |
|----|-----|-------|-------|--------------|
| **F1** | Align `build_target.py` layer keys with `erpnext_doctype_graph.json` `setup_layers` + `phase_mapping` | A · L3 | `target/build_target.py`, `test/test_build_target_layers.py` | Masters precede transactions; no spurious `layer_unknown` for standard mfg plan |
| **F2** | Remove silent F3iche template fallback; flag missing templates in assurance | A · L3 · L1 | `niche_resolver.py`, `discovery_assurance.py` | Trading transcript → `template_missing`, never jobshop seeds |
| **F3** | Wire F3iche `questions_to_ask` into clarify loop before generic MTS/MTO | B · L2 | `f3iche_seeds.py`, `discovery_clarify.py`, `discovery_chat.py` | Chemical niche asks Part A/B question from JSON |

### Phase B — Make target structure meaningful (P1)

| ID | Fix | Class | Files | Verification |
|----|-----|-------|-------|--------------|
| **F4** | Surface `warehouse_setup`, `default_settings.seeding_strategies` in `mvp_boundary.org_skeleton` | B · L3 | `f3iche_seeds.py`, `build_target.py` | Chemical plan includes RM/WIP/FG warehouse names |
| **F5** | Org-structure open assumptions (locations, fiscal year, cutover, multi-company) | C · L2 | `discovery_org_assumptions.py`, `discovery_assurance.py` | YELLOW lists open org facts when not in transcript |
| **F6** | Offline planner fallback forces YELLOW assurance | A · L1 | `discovery_assurance.py`, `discovery_chat.py` | `planner_offline_fallback` never GREEN |

### Phase C — Backlog (P2)

| ID | Fix | Notes |
|----|-----|-------|
| **F7** | Scale-aware Day-1 breadth in validator | Requires band rules in `mvp_validator.py` |
| **F8** | Ship `trading_fmcg_distributor.json` + `service_professional.json` | Unblocks non-manufacturing beta |
| **F9** | Fix field-service hints → not jobshop | `niche_resolver.py` hint table |

---

## Commit sequence

1. `docs: add Step 1 consultant review implementation plan`
2. `fix(discovery): align build_target layers with erpnext doctype graph`
3. `fix(discovery): stop silent F3iche template fallback and flag missing templates`
4. `feat(discovery): wire F3iche questions_to_ask into clarify loop`
5. `feat(discovery): surface org skeleton and org assumption flags in target/assurance`
6. `fix(discovery): force YELLOW assurance on offline planner fallback`

---

## Exit criteria (extends v9.5 gate)

- [x] Golden test: chemical manufacturing `setup_steps` — Item before Work Order
- [x] Golden test: trading niche never loads manufacturing template seeds
- [x] Clarify panel shows ≥1 niche-specific question for resolved manufacturing niche
- [x] `mvp_boundary.org_skeleton.required_warehouses` populated for chemical
- [x] `planner_offline_fallback` → assurance YELLOW
- [ ] Live matrix ≥80% (unchanged gate)
