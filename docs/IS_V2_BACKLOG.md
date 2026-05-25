# IS v2 — Backlog & Priorities

> **Detailed IS appendix** — full P0–P4 lists, golden run checklist, known issues.  
> **Master product priorities:** [`PRODUCT_BACKLOG.md`](./PRODUCT_BACKLOG.md) (weekly focus + Platform/Marketing/Design streams).  
> **Active sprint plan:** [`PRIORITIES.md`](./PRIORITIES.md) (tiers, day plan, launch definition).  
> **Stream tag:** IS — summarized in master under **Stream: IS**.

> **Living document** — ideas, fixes, features, and UI work for the Implementation System.  
> **Last reviewed:** 2026-05-25  
> **Owner:** Green Surface golden runs + corpus quality drive current ordering.

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

---

## North star (current)

> **Any Green Surface upload → correct doctype map → honest validate UI → safe phased ERPNext import** — without manual JSON edits or re-classifying files by hand.

Generalized: **corpus in, trustworthy preview out, import only when row-level quality passes.**

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

- **Sparse data → error or `partial`** — “critically sparse” warning should affect doctype status, not only sidebar text.
- **Overall validation status** — session-level `partial` when any doctype has warnings; readiness % should not show 100% in that state.
- **Validate preview: flatten child tables** — Stock Entry / Purchase Receipt show `item_code`/`qty` in UI (today `--` at top level after `fold_child_tables`).
- **UI badge semantics** — green “Passed” vs amber “Passed with warnings” vs red “Failed”.
- **Tier 1 quality gate** — deterministic rules before any LLM: empty identity, wrong source mix, row count vs dedupe expectation.
- **Structured `ValidationReport` JSON** — single artifact: per-doctype sources, row issues, classification confidence (feeds UI + supervisor).
- **Extend supervisor on validate** — enable `IS_SUPERVISOR_ENABLED=1`; feed quality report; ask targeted questions (“PR rows from `active_projects` — did you mean Project?”).
- **Supervisor scope today** — only missing field *keys* + WO enum auto-fix; expand to empty values and cross-file sanity.

---

## P2 — UX (Implementation Assistant & validate screen)

- **Chat bar at bottom of right panel** — persistent input on Validate (and later Sandbox): ask about gaps, answer supervisor prompts, trigger mapping refinement. *(Discussed in separate Cursor conversation.)*
- **Chat context wiring** — session id, validation report, mapped payloads summary, supervisor pending actions (avoid hallucinated row counts).
- **Validate: one panel per doctype** — show `source_files[]` and merged row count (partially done via `corpus_merge` + launcher).
- **Classification transparency** — per file: chosen doctype, score margin, method (`local` / `llm`); “wrong doctype?” affordance.
- **Import plan summary on Validate** — phases, merged record counts, blocked steps.
- **Wire chat → `refine_mapping_with_llm`** — user says “map party_name to supplier_name” → regen payload.

---

## P3 — Architecture (stop patching long-term)

- **Corpus model doc** — single diagram: upload wave → assign corpus → classify → split → map → merge-on-write → validate → finalize plan → import phases.
- **Per-file R2 keys + canonical merge blob** — optional if merge-on-write + guards are insufficient for audit/debug.
- **Unified merge policy** — all consumers use `corpus_merge.py` (map, validate, finalize, preview, import preflight).
- **File-aware import plan gating** — plan steps aware of which files contributed which doctypes.
- **Supervisor: one LLM call** — one structured report in, questions + auto_fix actions out (not multi-agent debate).
- **Tiered resolution** — (1) KB + priors, (2) LLM classify if ambiguous, (3) LLM column map for unmapped cols only, (4) live schema fallback when sandbox credentials exist.
- **Align with `ARCH_V2_VISION.md`** — track which backlog items are “v1.5 hardening” vs true v2 agentic path.

---

## P4 — Deferred / experiments

- **Multi-agent “nodes report to supervisor”** — deferred; one validation report → one supervisor call is enough for now.
- **Auto-reclassify file from chat** — “this is Project not PR” → re-run map for one file only.
- **Full live-schema mapping** — replace static KB for unknown doctypes (v2 vision).

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


---

## Known issues from latest validate UI (Green Surface)


| Symptom                                                                         | Likely cause                                                             | Backlog ref                             |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------- |
| Purchase Receipt includes `05_gs_active_projects.csv`, 5 rows, sparse warehouse | Still classified as PR or stale session; merge kept bad rows             | P0 cross-file guard, P0 Project confirm |
| Supplier 8 rows, empty names on rows 3–4                                        | Customer rows in Supplier bucket + `__anon_`* dedupe                     | P0 merge quarantine, P0 customer leak   |
| Stock Entry `--` for item/qty                                                   | Child table folded; preview shows parent columns only                    | P1 flatten preview                      |
| All panels PASSED, 100% readiness                                               | Warnings don’t fail status                                               | P1 badge + readiness                    |
| No Project panel                                                                | `active_projects` mapped to PR                                           | P0 Project classification               |
| BOM shows 2 rows                                                                | Likely correct (2 FGs); 3 CSV lines = 2 BOMs + components in child table | Verify in harness matrix                |


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

---

## Review log


| Date       | Reviewer              | Changes                                                 |
| ---------- | --------------------- | ------------------------------------------------------- |
| 2026-05-25 | IS golden run session | Initial backlog from Green Surface gaps + chat bar idea |


