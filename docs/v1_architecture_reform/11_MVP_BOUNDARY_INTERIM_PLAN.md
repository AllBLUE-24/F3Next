# MVP Boundary — Interim Engineering (While Research Expands Catalog)

> **Status:** Active  
> **Parallel to:** Research adding 30–50 sector-grouped archetypes to `containers/discovery/kb/archetype_catalog.json`  
> **Parent:** [`10_MVP_BOUNDARY_V1_PLAN.md`](./10_MVP_BOUNDARY_V1_PLAN.md)

---

## Goal

Make MVP boundary work for **any bottleneck message** without new Python patches per archetype. Research owns KB rows; engineering owns **registry, validation, LLM/scoping resilience, and deprecation of legacy paths**.

---

## What Research adding 30–50 archetypes fixes vs does not

| Fixed by catalog growth | Still engineering-owned |
|-------------------------|-------------------------|
| More `signals[]` for signal-match fallback | Niche template pick (wrong F3iche) |
| More `day1_seed_hints` for scoping | LLM picking wrong/invalid `archetype_id` |
| Richer recommend prompt hints | Seeds outside template (graph extension rules) |
| Sector organization for Research | GM-DISC-04 until `custom_order_pipeline` exists |

---

## Interim engineering work (this sprint)

### A. Registry & validation (no hardcoded ID lists)

1. **`validate_archetype_registry()`** — CI checks: duplicate ids, missing hints, hints not in doctype graph, bad id format, empty signals.
2. **CLI** — `python -m containers.discovery.kb.validate_archetypes` for Research pre-merge check.
3. **Tests** — golden validation on current catalog + chemical F3iche.

### B. LLM hint surface scales with catalog

4. **`build_bottleneck_hint_context`** — use `merged_archetypes(f3iche_id)` so global catalog + F3iche overrides both appear in recommend prompt (not either/or).
5. **Optional sector headers** — if `_meta.sectors` present in catalog, group hints for LLM readability.

### C. Scoping resilience

6. **Invalid `archetype_id`** — if LLM returns unknown id, log + fall back to signal match (already partial; add trace fields `invalid_archetype_id`).
7. **Keep legacy regex/map behind flags** — defaults off; deprecate map file.

### D. Phase 6 soft (not delete yet)

8. Mark `mvp_bottleneck_map.json` deprecated.
9. Default `DISCOVERY_USE_MVP_MAP_FALLBACK=false`.
10. Document in `09_CORE_KB_AND_STEPWISE_MIGRATION.md` + backlog.

### E. Blocked on Research (do not code workarounds)

- GM-DISC-04 `custom_order_pipeline` archetype row.
- ISO/incoming QC archetype with `Quality Inspection` in `day1_seed_hints`.
- Sector taxonomy final names in `_meta.sectors`.

---

## Input needed from Research

See [`containers/discovery/kb/RESEARCH_HANDOFF.md`](../../containers/discovery/kb/RESEARCH_HANDOFF.md).

Priority archetypes before bulk 50:

1. **`custom_order_pipeline`** — Quotation, Sales Order, Project; defer Work Order/Job Card.
2. **`incoming_quality_compliance`** (or agreed id) — Quality Inspection, Quality Inspection Template, Batch, Purchase Receipt.
3. **Confirm snake_case id convention** and no duplicate ids across catalog vs F3iche unless intentional override.

Each new row must include: `archetype_id`, `primary_bottleneck`, `signals[]` (≥5), `functional_requirements[]`, `day1_seed_hints[]` (ERPNext doctype names), `defer_typically[]`, `notes`.

Run before PR: `python -m containers.discovery.kb.validate_archetypes`

---

## Done when (interim gate)

- [ ] Validation CLI passes on catalog + chemical F3iche
- [ ] Recommend prompt receives merged catalog + F3iche hints
- [ ] Golden GM-DISC-01..03 green with legacy flags off
- [ ] GM-DISC-04 activated when Research lands archetype
- [ ] Live harness spot-check on 2 user transcripts

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-06 | Interim plan + validation CLI + merged hint context + Phase 6 soft defaults |
