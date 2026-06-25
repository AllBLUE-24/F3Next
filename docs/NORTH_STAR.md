# F3Next North Star — Agent Shell + Golden Truth

> **Status:** Active program definition (supersedes “ship features on four IS routes”)  
> **Last updated:** 2026-06-06 — Track A (Truth) complete  
> **Audience:** Engineering, product, agents  
> **Program folder:** [`v1.0.0/`](./v1.0.0/) — foundation branches remain; **exit criteria** now flow through this doc set.

This is the **single product north star** for F3Next v1.0.0. The old v1.0.0 program (Company Brain, four gates, foundation branches) is still valid infrastructure — but **what users see and what “ready” means** is defined here.

---

## One sentence

**One agent window (like Cursor), one golden matrix that must stay green, one presentation layer that never leaks pipeline debug — IS and OS share the same tree; IS adds the file/mapping/import branch.**

---

## The three canonical artifacts

| # | Document | Owns |
|---|----------|------|
| 1 | [**NORTH_STAR_AGENT_SHELL.md**](./NORTH_STAR_AGENT_SHELL.md) | 3-pane UI, gate renderer, drawer contracts, signal collapse, IS/OS shared shell, deprecation list |
| 2 | [**GOLDEN_MATRIX_MANIFEST.md**](./GOLDEN_MATRIX_MANIFEST.md) | Frozen Green Surface `3rd_run` + chemical f3iche — per-file doctype, columns, KB synonyms, expected map/validate outcomes, harness row IDs |
| 3 | [**PRESENTATION_AGENT_CONTRACT.md**](./PRESENTATION_AGENT_CONTRACT.md) | Presentation LLM node — inputs, outputs, forbidden debug fields, `user_turn` routing, copy rules |

**Read order:** Shell (what users touch) → Golden matrix (what “ready” means) → Presentation agent (how the shell speaks).

---

## What changed from “v1.0.0 as branch program”

| Before | North star now |
|--------|----------------|
| Four IS routes (Upload / Analyze / Validate / Import) each with own cards, signals, confirmations | **One main stream** + **right drawer** for inspection |
| Supervisor + chat + PromptCard + readiness synth + quality_gate rows | **One active gate** rendered inline (MCQ / upload / confirm) |
| “Foundation branches merged” = ready | **`GOLDEN_MATRIX_MANIFEST` all required rows green** + user completes loop in shell |
| `summary_for_ui` and internal node names in chat | **Presentation agent** — structured user copy only |
| KB “~15 doctypes, expand later” | **KB scoped to golden matrix** — new doctype = new harness row before “supported” |

Foundation branches ([`v1.0.0/BRANCH_STRATEGY.md`](./v1.0.0/BRANCH_STRATEGY.md)) deliver **L0–L4 plumbing**. This north star delivers **L5 surface + L1 honesty + L3 KB proof** for beta.

---

## IS + OS — same tree

```text
F3Next Session (project_id)
├── Shared spine
│   ├── Company Brain (LER, CVS hints, context, honesty)
│   ├── Four gates: RESOLVE → COMPLETE → CLARIFY → COMMIT
│   ├── Agent shell (sidebar + stream + drawer)
│   └── Presentation agent (user-facing copy + actions)
├── IS branch (when mode = implementation)
│   ├── Corpus ingest (+ re-upload merge)
│   ├── Classify → map → validate → phased import
│   └── Drawer: mapped files, validation preview, import plan
└── OS branch (when mode = operations)
    ├── NL intent → plan → execute
    └── Drawer: command plan, payload preview, execute result
```

Temporal workflows stay **separate** (`ImplementationWorkflow`, `ERPOSCommandWorkflow`). The **UI and `user_turn` contract** are shared.

Detail: [`v1.0.0/PLATFORM_OVERVIEW.md`](./v1.0.0/PLATFORM_OVERVIEW.md) (brain), [`NORTH_STAR_AGENT_SHELL.md`](./NORTH_STAR_AGENT_SHELL.md) (surface).

---

## Definition of Done (v1.0.0-rc)

A release candidate is allowed **only** when all pass:

| Gate | Criterion | Doc |
|------|-----------|-----|
| **G0 Shell** | User completes Green Surface loop without visiting legacy-only confirmation pages | Agent shell § Migration |
| **G1 Golden** | All **required** rows in golden manifest green in CI | Golden matrix § Harness |
| **G2 Honesty** | UI `stage` matches workflow wait reason (one banner, no “thinking” while blocked on user) | Agent shell § Gate renderer |
| **G3 Presentation** | No `summary_for_ui`, node names, or RAG block lists in user stream | Presentation agent § Forbidden |
| **G4 Brain** | LER + gates per [`RELEASE_v1_0_0.md`](./v1.0.0/RELEASE_v1_0_0.md) §2.3–2.4 | Existing release doc |

**Explicitly not required for rc:** every ERPNext doctype, full v2 reasoning agent, mic UI.

---

## Execution tracks (parallel, capped at 5 active — [`PRIORITIES.md`](./PRIORITIES.md))

```text
Track A — Truth       ✅ COMPLETE — Golden matrix harness green, Stock Entry KB fixed (GM-FILE-04)
Track B — Shell       Agent shell layout + gate renderer + drawer (IS first)
Track C — Presentation Presentation agent + chat mirror fix (no debug leakage)
Track D — Foundation  Complete remaining v1.0.0 branch merges (LER, gates) — already largely in repo
Track E — Expand      New doctype / industry only with new golden row
```

**Track A status (2026-06-06):** All 5 Golden Matrix tests passing. Stock Entry synonyms added. `GM-FILE-04` and `GM-E2E-03` are GREEN.

Do **not** start Track E until Track A is green for the current MVP doctype set. ✅ **CONDITION MET**

---

## Relationship to other docs

| Doc | Role under north star |
|-----|----------------------|
| [`FOUNDATIONS.md`](./FOUNDATIONS.md) | L0–L5 triage — still law for every PR |
| [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) | Pillar status — update when golden row ships |
| [`ARCH_V2_VISION.md`](./ARCH_V2_VISION.md) | Long horizon — live schema; not beta blocker |
| [`ARCH_IMPLEMENTATION.md`](./ARCH_IMPLEMENTATION.md) | Current pipeline — migrate UI away, keep activities |
| [`v1.0.0/`](./v1.0.0/) | Foundation branch execution detail |

---

## Agent checklist (every change)

1. Restate symptom in **user** terms.  
2. Layer **L0–L5** + IS pillar **1–10**.  
3. Classify **A/B/C/D** ([`FOUNDATIONS.md`](./FOUNDATIONS.md)).  
4. If mapping/validate failure on golden file → check **golden row** first (KB vs code).  
5. If UI confusion → check **shell contract** before adding a new component.  
6. Update **golden manifest** or **backlog line** before merge.

---

*This document is the product north star. Tag `v1.0.0-rc` when § Definition of Done passes.*
