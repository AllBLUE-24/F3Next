# IS v2 — Backlog & Priorities

> **Detailed IS appendix** — full P0–P4 lists, golden run checklist, known issues.  
> **Master product priorities:** [`PRODUCT_BACKLOG.md`](./PRODUCT_BACKLOG.md) (weekly focus + Platform/Marketing/Design streams).  
> **Active sprint plan:** [`PRIORITIES.md`](./PRIORITIES.md) (tiers, day plan, launch definition).  
> **Stream tag:** IS — summarized in master under **Stream: IS**.

> **Living document** — ideas, fixes, features, and UI work for the Implementation System.  
> **Last reviewed:** 2026-05-26  
> **Owner:** Green Surface beta + universal IS foundations drive current ordering.

**Related docs**

- `[PRODUCT_BACKLOG.md](./PRODUCT_BACKLOG.md)` — product-wide master backlog & weekly priorities
- `[ARCH_IMPLEMENTATION.md](./ARCH_IMPLEMENTATION.md)` — current pipeline architecture
- `[ARCH_V2_VISION.md](./ARCH_V2_VISION.md)` — long-term “reasoning agent” direction (not this queue)

---

## Rules (anti-patching)

1. **Every fix gets a line here** before or right after merge — or we explicitly reject it as one-off.
2. **Re-prioritize after each golden run** (Green Surface 8-file corpus is the reference).
3. **P0 before P2** — don’t build chat UX on top of a validate screen that lies.
4. **Prefer structural fixes** (corpus model, merge policy, validation schema) over one-off filename priors.
5. Mark items **Done** with date + brief note; don’t delete history.
6. **Status sync:** tier tables in [`PRIORITIES.md`](./PRIORITIES.md) are authoritative for sprint items; use `[x]` here when shipped.
7. **Agent checklist:** classify every fix as A/B/C/D, assign layer L0–L5 and pillar 1–10 before coding. See [`FOUNDATIONS.md`](./FOUNDATIONS.md).

---

## North star

### Near-term (v1.5 — Green Surface beta)

> **Any Green Surface–class upload → correct doctype map → honest validate UI → safe phased ERPNext import** — without manual JSON edits or re-classifying files by hand.

Corpus in, trustworthy preview out, import only when row-level quality passes.

### Long-term (universal IS)

> **Any tabular upload → correct doctype(s) → complete mapped payload → honest validate → safe phased import** — with supervisor questions only when the user must supply or confirm data, never for pipeline bugs.

Detail: [`ARCH_V2_VISION.md`](./ARCH_V2_VISION.md). Bridge items: **P3 — Universal IS foundations** below and [`PRIORITIES.md`](./PRIORITIES.md) Tier 7.

---

## IS fundamental pillars (product-level)

Ten layers that must hold for “any doctype / any data” to work. Track implementation status here; sprint ordering in [`PRIORITIES.md`](./PRIORITIES.md).

| # | Pillar | Goal | Status | Backlog |
|---|--------|------|--------|---------|
| 1 | **Universal ingestion & corpus** | Upload wave → unified corpus; re-uploads merge | ~70% | P3 corpus model |
| 2 | **Parse & normalize structure** | CSV/TSV/XLSX/JSON → rows + columns; R2 manifest v2 + LLM corpus understanding | ~85% | Column-map LLM fallback (tiered resolution) |
| 3 | **Intent & classification** | F3iche: registry scorer + LLM when ambiguous; mapping uses corpus hints | ~75% | P2 transparency; column-map LLM fallback |
| 4 | **Signaling & synonyms** | KB priors + aliases; LLM when no match | ~50% | P3 synonym growth; ~15 doctypes today |
| 5 | **ERP knowledge (static + live)** | Schema, child tables, links, lifecycle, phases, deps | ~40% | P3 SchemaResolver v1; validation_rules |
| 6 | **Industry & company context** | F3iche + pgvector RAG + profile | ~80% Steps 6–8 | Step 8 corpus-aware seeds, mvp_boundary.json, action reconcile *(2026-06-05)* |
| 7 | **Mapping & merge** | Column→field, party split, dedupe, defaults | Strong for GS | P0 done; P3 unified merge |
| 8 | **Gap analysis & supervisor** | MVP seed scope; party-split; default-aware assumptions; supervisor soft messaging | ~65% | P1 post-mapping readiness recheck |
| 9 | **Validation & trust gate** | pass / partial / fail; block bad import | Validate + sidebar aligned on Validate route | Tier 7c for full ValidationReport |
| 10 | **Phased import & verify** | Order, link resolution, idempotency, submit policy | ~70% | lifecycle.py; import idempotency shipped |

**Supported doctypes today (KB mapping modules):** Item, Customer, Supplier, BOM, Work Order, Project, Purchase Receipt, Stock Entry, Sales Order, Sales Invoice, Purchase Order, Payment Entry, Journal Entry, Employee, Batch (~15 of 400+ ERPNext doctypes).

---

## Priority legend


| Tier   | Meaning                                                    | Examples                                               |
| ------ | ---------------------------------------------------------- | ------------------------------------------------------ |
| **P0** | Wrong or junk data could reach ERPNext; golden run blocked | Empty supplier names, project file in Purchase Receipt |
| **P1** | User sees green “Passed” but shouldn’t trust it            | Warnings ignored, 100% readiness with sparse rows      |
| **P2** | UX clarity & operator speed                                | Chat bar, child-table preview, amber badges            |
| **P3** | Architecture that reduces future patching                  | Unified corpus model, ValidationReport schema          |
| **P4** | Experiments / nice-to-have                                 | Multi-agent supervisor debate                          |


---

## P0 — Blockers (do first)

- [x] **Row-level required values** — validation fails on empty identity/mandatory values. *(2026-05-25)*
- [x] **Merge quarantine** — no `__anon_*` rows; missing dedupe key dropped at merge. *(2026-05-25)*
- [x] **Cross-file merge guard** — filename priors remap incompatible files (e.g. `active_projects` → Project). *(2026-05-25)*
- [ ] **Confirm Project classification live** — restart worker + fresh session (not stale R2).
- [x] **Green Surface 8-file harness** — matrix: [`GREEN_SURFACE_GOLDEN_MATRIX.md`](../containers/implementation/dev_fixtures/GREEN_SURFACE_GOLDEN_MATRIX.md)
- [x] **Customer rows in Supplier payload** — quarantine + cross-entity validation. *(2026-05-25)*

---

## P1 — Quality & trust (validate must not lie)

- [x] **UI badge semantics** — green “Passed” vs amber “Passed with warnings” vs red “Failed” on Validate screen. *(2026-05-25 — `DataPreviewTable`, `ValidateView`)*
- [x] **Validate preview: flatten child tables** — Stock Entry / Purchase Receipt show `item_code`/`qty` via `preview_flatten.py` + launcher. *(2026-05-25 — live golden verify pending)*
- [x] **Overall validation status (Validate page)** — session-level `partial` when any doctype has warnings; `validation_overall` + capped data quality score. *(2026-05-25)*
- [x] **Sparse data → `partial` (validation engine)** — warnings flip doctype status from pass to partial. *(2026-05-25 — `test_activities.py`)*
- [x] **Post-mapping readiness (sidebar on Validate)** — validation summary card replaces pre-mapping score on validate/sandbox routes. *(2026-05-26 — `SupervisorPanel.tsx`; full backend recheck → Tier 7c)*
- [x] **Confirm-button UX (Analyze + Validate)** — optimistic confirm lock + Validate step from stage API / sessionStorage. *(2026-05-26)*
- [x] **Tier 1 quality gate** — deterministic rules before any LLM: empty identity, wrong source mix, filename/doctype conflicts. *(2026-06-04 — `evaluate.py` + validate primary)*
- [x] **Structured `ValidationReport` JSON** — R2 + launcher API with `source_files[]` per check. *(2026-06-04 — `shared/models/validation_report.py`)*
- [ ] **Extend supervisor on validate** — enable `IS_SUPERVISOR_ENABLED=1`; feed quality report; ask targeted questions (“PR rows from `active_projects` — did you mean Project?”).
- [ ] **Supervisor scope expansion** — empty values and cross-file sanity (today: missing field *keys* + WO enum auto-fix only).
- [x] **Supervisor contract** — `ask_user` only for user-resolvable data gaps; cross-file + empty value paths. *(2026-06-04 — `supervisor_agent/contract.py`)*
- [x] **Step 8c MVP-scoped readiness** — scan `seed_doctypes` not full graph; party-split Role→Customer/Supplier; corpus-positive signals; `field_policy` default-aware assumptions; R2 target load for seeds/deferred; Green Surface `3rd_run` golden tests. *(2026-06-05 — L3–L4 pillar 8, class A)*
- [x] **Step 8c readiness report R2 + seed refine** — `data_readiness_report.json` in R2; `refine_mvp_seeds` injects Customer/Supplier, defers Item Variant/Quotation/Delivery Note/Task/Timesheet without file evidence; phase_d→Important; embedded Project note; Ready list in supervisor UI. *(2026-06-05 — L3–L4 pillar 8, class A)*
- [x] **Field-level readiness + tiered column map** — `is_common/required_fields` shared with validate; Step 8c `assess_field_coverage` blocks on graph-required fields; KB exact → LLM → KB fuzzy mapping (`Vendor_Name`→`supplier`, `Target_Date`→`delivery_date`); relative date defaults; mapping preflight; Green Surface `3rd_run` golden tests. *(2026-06-05 — L3–L4 pillars 7–8, class A)*

---

## P2 — UX (Implementation Assistant & validate screen)

- [x] **Chat bar at bottom of right panel** — persistent input on Validate/Analyze/Import routes; `is_chat_messages` + `/api/implementation/chat`. *(2026-06-01)*
- [x] **Chat context wiring** — session id, validation report, mapped payloads summary, supervisor pending actions. *(2026-06-01)*
- [x] **Wire chat → `refine_mapping_with_llm`** — mapping refinement from natural language. *(2026-06-01)*
- [x] **Chat answers supervisor prompts** — free-text / continue / upload routes to `supervisor-prompts/respond`. *(2026-06-01 Phase 3)*
- [x] **Supervisor + quality gate messages in chat stream** — system/assistant bubbles for auto-fix, user_gap, supervisor questions. *(2026-06-01 Phase 3)*
- **Validate: one panel per doctype** — show `source_files[]` and merged row count. *(partially done — `corpus_merge` + launcher)*
- **Classification transparency** — per file: chosen doctype, score margin, method (`local` / `llm`); “wrong doctype?” affordance.
- **Import plan summary on Validate** — phases, merged record counts, blocked steps.

---

## P2b — Closed feedback loops (quality gate)

> Branch: `feature/is-chat-bar-phase1` · Phases 1–3 shipped in repo; enable via env flags before beta.

- [x] **Shared `quality_gate` activity** — deterministic rules + optional LLM (`QUALITY_GATE_LLM=1`). *(2026-06-01)*
- [x] **IS step contracts** — classify, map, validate, finalize, import. *(2026-06-01)*
- [x] **OS step contracts** — extract_intent, validate_payload (+ hooks for plan/execute). *(2026-06-01)*
- [x] **IS workflow gates on all major steps** — behind `IS_QUALITY_GATE_ENABLED=1`. *(2026-06-01 Phase 3)*
- [x] **Gate verdicts → chat + audit** — `quality_gate_verdict` in `is_audit_trail`; user-visible system messages. *(2026-06-01 Phase 3)*
- [x] **Retry injection into activity inputs** — gate `retry_feedback` passed into map/validate nodes. *(2026-06-04 — workflow retry loop)*
- [ ] **OS persistent chat history** — mirror IS `is_chat_messages` pattern for NL commands
- [ ] **Quality gate unit tests in CI golden matrix** — one row per verdict class

---

## P3 — Architecture (stop patching long-term)

- [x] **Manifest v2 + corpus understanding (Step 2)** — `file_meta` (columns, row_count, sample_rows) + LLM `enrich_corpus_understanding`; gap_analyzer respects `explicitly_not_doctypes`. *(2026-06-05 — L2 pillar 2, class A)*
- [x] **Tiered F3iche inference (Step 3)** — `signals_scorer` implements registry rules; LLM only when ambiguous; discovery prior; principle-based corpus prompt + validation. *(2026-06-05 — L2 pillar 3, class A)*
- [x] **F3iche confirmation synthesis (Step 3.5)** — discovery chat + file signals merged into `f3iche_confirmation` proposal; Yes/No + free-text correction gate replaces niche dropdown; verify step compares user vs synthesis. *(2026-06-05 — L4 pillar 3, class A)*
- [x] **Discovery-aware F3iche routing fixes** — OpenAI default for `generate_typed`; router falls through on provider ValueError; broad discovery `manufacturing` maps via industry/chat hints; registry false-positive fixes (garment size suffix, structural 500); fresh hooks discovery at infer; synthesis fallback uses discovery resolver. *(2026-06-05 — L0+L2 pillar 3, class A)*
- [x] **OpenAI structured output repair (Step 2b)** — json_object + schema system prompt + `repair_pydantic_dict` for missing `corpus_summary`; Gemini cross-fallback opt-in only (`LLM_ALLOW_GEMINI_FALLBACK`). *(2026-06-05 — L0 pillar 2, class A)*
- **Corpus model doc** — single diagram: upload wave → assign corpus → classify → split → map → merge-on-write → validate → finalize plan → import phases.
- **Per-file R2 keys + canonical merge blob** — optional if merge-on-write + guards are insufficient for audit/debug.
- **Unified merge policy** — all consumers use `corpus_merge.py` (map, validate, finalize, preview, import preflight).
- **File-aware import plan gating** — plan steps aware of which files contributed which doctypes.
- **Supervisor: one LLM call** — one structured report in, questions + auto_fix actions out (not multi-agent debate).
- **Tiered resolution** — (1) KB + priors, (2) LLM classify if ambiguous, (3) LLM column map for unmapped cols only, (4) live schema fallback when sandbox credentials exist.
- **Align with `ARCH_V2_VISION.md`** — track which backlog items are “v1.5 hardening” vs true v2 agentic path.

---

## P3 — Universal IS foundations (v1.5 → v2 bridge)

> **North star:** any tabular upload → correct doctype map → honest validate → safe import.  
> v2 detail: [`ARCH_V2_VISION.md`](./ARCH_V2_VISION.md). Sprint ordering: [`PRIORITIES.md`](./PRIORITIES.md) Tier 7.

- [ ] **Corpus-first model** — single canonical merge blob per session wave; all nodes read/write via `corpus_merge.py`
- [x] **`validation_rules.json` as primary validate source** — KB `is_import_rules` primary in `validation_agent/activities.py` (branch 04)  
- [ ] **SchemaResolver v1** — live Frappe schema for KB-miss doctypes on classify + validate + import preflight (extend `live_schema.py` beyond mapping-only path today)
- [ ] **Post-mapping readiness recheck** — sidebar score from ValidationReport, not pre-mapping 8c assessment only
- [ ] **Supervisor contract + tests** — `ask_user` only for user-resolvable data gaps; pipeline bugs → auto_fix or fail
- [ ] **Classification transparency** — per file: doctype, confidence, method (`local` / `llm` / `live`)
- [ ] **Synonym KB growth process** — promote column/filename priors from golden + beta runs into KB modules (`filename_priors.json`, `column_priors.json`, mapping `*.json`)
- [ ] **`module_docs` seeding** — curated doctype docs → pgvector; reduce noise from scraped `erpnext_docs`
- [ ] **Parse roadmap** — v1.5: CSV/TSV/XLSX solid; v2: PDF / WhatsApp exports / messy TXT
- [ ] **pgvector as primary classify signal (v2 milestone)** — promote RAG from annotation-only to co-primary with KB priors for unknown terminology

---

## P4 — Deferred / experiments

- **Multi-agent “nodes report to supervisor”** — deferred; one validation report → one supervisor call is enough for now.
- **Auto-reclassify file from chat** — “this is Project not PR” → re-run map for one file only.
- **Full live-schema agent** — replace static KB entirely for unknown doctypes (v2 vision; distinct from SchemaResolver v1 bridge in P3).
- **Business graph in DB** — `erp_setup_graph` + `erp_safe_defaults` tables per ARCH_V2_VISION (v2; JSON graph sufficient for v1.5).
- **Auto-learn synonyms from user corrections** — chat/refine_mapping feedback → KB promotion pipeline.

---

## Done (recent)


| Date       | Item                                                       | Notes                                                                      |
| ---------- | ---------------------------------------------------------- | -------------------------------------------------------------------------- |
| 2026-05-25 | Modular KB split                                           | `schema/mapping/*.json`, `compose.py`, `index.json`                        |
| 2026-05-25 | `Project.json` + Supplier/Customer synonyms                | `party_name`, `party_group`                                                |
| 2026-05-25 | Filename + column priors in KB                             | `active_projects` → Project (when worker on new code)                      |
| 2026-05-25 | Merge-on-write at map time                                 | `corpus_merge.py`, dedupe by KB policy                                     |
| 2026-05-25 | `finalize_import_plan` aggregate + inject missing doctypes | e.g. Project → `phase_d_projects`                                          |
| 2026-05-25 | Validate preview merged by doctype                         | `is_launcher.get_validate_preview`                                         |
| 2026-05-25 | Party split always-map                                     | `always_map_split_entities` + `_should_map_doctype(from_party_split=True)` |
| 2026-05-25 | Pass 2.5 link resolution                                   | `link_resolver.py` warehouse aliases                                       |
| 2026-05-25 | Pass 2.6 BOM auto-submit                                   | `lifecycle.py`                                                             |
| 2026-05-25 | Tier 0 demo unblock | naming_series at map + validate; supervisor obsolete prompts; auto_fix apply_kb_defaults |
| 2026-05-25 | Data readiness + supervisor gate                           | Pre-validate                                                               |
| 2026-05-25 | Import idempotency (BOM, WO, dedupe keys)                  | `import_idempotency.py` + tests                                            |
| 2026-05-25 | Validate partial status + preview flatten                  | `validation_agent` partial on warnings; `preview_flatten.py` + launcher    |
| 2026-05-26 | Tier 1b validation sidebar + Tier 1e confirm UX            | `SupervisorPanel`, `AnalyzeView`, `ValidateView`                           |
| 2026-05-26 | Foundations closure sprint                                 | `FOUNDATIONS.md`, baseline seed order, `complete_with_errors`, import-results UI, re-finalize API |
| 2026-05-26 | Greenfield setup wizard in Phase A                         | `ERPNextAdapter.run_setup_wizard`, `site_prerequisites.run_greenfield_setup_wizard` |


---

## Known issues from latest validate UI (Green Surface)


| Symptom                                                                         | Likely cause                                                             | Backlog ref                             |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------- |
| Purchase Receipt includes `05_gs_active_projects.csv`, 5 rows, sparse warehouse | Still classified as PR or stale session; merge kept bad rows             | P0 cross-file guard, P0 Project confirm |
| Supplier 8 rows, empty names on rows 3–4                                        | Customer rows in Supplier bucket + `__anon_`* dedupe                     | P0 merge quarantine, P0 customer leak   |
| Stock Entry `--` for item/qty                                                   | Was folded preview; `preview_flatten.py` shipped — **verify live**       | P1 flatten preview (done in repo)       |
| All panels PASSED, 100% readiness (Validate)                                    | Warnings → partial on Validate page *(fixed)*; **sidebar** still pre-mapping | P1 1d done; **1b pending**          |
| No Project panel                                                                | `active_projects` mapped to PR                                           | P0 Project classification               |
| BOM shows 2 rows                                                                | Likely correct (2 FGs); 3 CSV lines = 2 BOMs + components in child table | Verify in harness matrix                |
| F3iche / mapping approve button still visible after click                       | Stage polling lag; card not hidden when stage advances                   | P1 confirm-button UX — **fixed 2026-05-26** |
| Validate “Validate & Confirm” reappears on refresh                              | Local `step` state not persisted                                         | P1 confirm-button UX — **fixed 2026-05-26** |
| Sidebar “Pre-mapping assessment” shows 100% while validate has warnings         | Post-mapping recheck not built                                             | P1 1b — **fixed 2026-05-26** on validate route |


---

## Golden run checklist (repeat after P0 batch)

1. Fresh `is_sessions` row + all 8 Green Surface files uploaded.
2. Worker on latest code (restart after KB/merge changes).
3. Validate: 8 doctype panels (not 8 duplicate Supplier), correct row counts.
4. No PR source containing `active_projects`.
5. Supplier count = 6 unique names.
6. Project = 2 rows.
7. Import phases B/C complete on sandbox (or dry-run preflight clean).

---

## Idea inbox (unprioritized)

*Add raw ideas here; promote to P0–P4 on review.*

- Chat bar also on Upload step (“here’s my vendor list and BOMs in one zip”).
- Export validate report as PDF for customer sign-off.
- Diff view: previous upload wave vs current merged corpus.
- User-editable merge dedupe keys per session.
- “Trust score” per doctype 0–100 for sales demo.
- Beta session log template per customer (see [`green-surface-firstmeet.md`](../green-surface-firstmeet.md)).

---

## Review log


| Date       | Reviewer              | Changes                                                 |
| ---------- | --------------------- | ------------------------------------------------------- |
| 2026-05-25 | IS golden run session | Initial backlog from Green Surface gaps + chat bar idea |
| 2026-05-26 | Green Surface beta prep | Added 10 IS pillars, universal north star, P3 bridge items, supervisor contract, UI confirm-button gaps |
| 2026-05-26 | Tier 1 status sync | Marked P1 badge/flatten/partial done; 1b sidebar + 1e buttons still open |
| 2026-05-26 | Tier 1 complete | 1b + 1e shipped on feature/is-trust-v2 |
| 2026-06-01 | Chat bar + quality gate Phases 1–3 | IS/OS feedback loops, full IS gate coverage, chat convergence on `feature/is-chat-bar-phase1` |


