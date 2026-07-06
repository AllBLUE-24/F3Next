# Discovery Archetype Routing — Engineering Plan

> **Status:** Active  
> **Parent:** [`10_MVP_BOUNDARY_V1_PLAN.md`](./10_MVP_BOUNDARY_V1_PLAN.md)  
> **Parallel:** Research signal-saturation pass on `archetype_catalog.json`

---

## Problem (from live harness)

The **scoping body** executes KB `day1_seed_hints` correctly when given the right `archetype_id`.  
The **recommend brain** (LLM) often picks the wrong id — WIP → `custom_order_pipeline`, procurement → `incoming_quality_compliance`.

Golden pytest passes because it **pre-feeds** `archetype_id`. Live harness exposes recommend accuracy (~40% on ad-hoc batch).

Research cannot verify signal improvements until engineering exposes **shadow signal rankings** on every run (`signal_match_score: null` with `mvp_focus` is expected, not a bug).

---

## Engineering phases

### Phase 1 — Observability (this sprint) ✅ in progress

**Goal:** Every `mvp_boundary.json` shows what signals would have picked vs what LLM picked.

| Task | Deliverable |
|------|-------------|
| P1.1 | `signal_match_candidates[]` — top-5 ids + scores, always computed |
| P1.2 | `llm_archetype_signal_score` — signal score of LLM-chosen id (0 if unknown) |
| P1.3 | `archetype_routing_mismatch` + note when top signal beats LLM id by ≥2 |
| P1.4 | Harness `--report` + optional `--expect-archetype` |
| P1.5 | Tests + doc for Research |

**Does not change routing behavior.**

### Phase 2 — Recommend guardrails (next)

| Task | Deliverable |
|------|-------------|
| P2.1 | Coerce `archetype_id` `"null"` / invalid → signal fallback |
| P2.2 | Validate id ∈ `list_archetype_ids(f3iche_id)` after recommend |
| P2.3 | Copy `functional_requirements` from KB row after id pick (LLM stops inventing) |
| P2.4 | Optional flag: `DISCOVERY_SIGNAL_OVERRIDE_MIN_MARGIN=2` — use top signal when LLM id score much lower |
| P2.5 | Tighten recommend prompt (one id from list; sector grouping) |

### Phase 3 — Niche + template fit

| Task | Deliverable |
|------|-------------|
| P3.1 | Reduce false `manufacturing_project_chemical` from keyword "chemical"/"epoxy" |
| P3.2 | Enable `DISCOVERY_LLM_NICHE_RESOLVE` for harness A/B |
| P3.3 | Graph-extend service doctypes (Warranty Claim, Issue) outside F3iche template |

### Phase 4 — LLM enhancement layer (defer or implement)

| Task | Deliverable |
|------|-------------|
| P4.1 | Implement `_enhance_seeds_from_discovery` **or** remove from contract |
| P4.2 | Clarify to Research: enhancement ≠ archetype routing |

### Phase 5 — Live golden matrix + gate

| Task | Deliverable |
|------|-------------|
| P5.1 | 10–15 harness transcripts with `--expect-archetype` |
| P5.2 | Nightly live LLM job; track archetype accuracy |
| P5.3 | **Step 1 complete** when ≥80% on matrix + GM-DISC-01..04 green |

---

## Research ↔ Engineering contract

| Field | Owner | Consumer |
|-------|-------|----------|
| `signals[]` | Research | Signal match + Adi listen hints in recommend prompt |
| `functional_requirements[]` | Research (Phase 2: copied from KB, not LLM-invented) | Scoping trace / future rules |
| `day1_seed_hints[]` | Research | `scope_mvp_seeds` |
| `notes` | Research | Recommend prompt context for Adi |

---

## Verification

```powershell
pytest containers/discovery/test/ -q
python -m containers.discovery.test.harness_mvp_boundary --transcript-file fixtures/green_surface_wip.txt --report
python -m containers.discovery.test.harness_mvp_boundary --transcript-file story.txt --report --expect-archetype factory_wip_bridge
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-07 | Phase 1 observability plan + implementation |
