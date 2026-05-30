# F3Next — Foundations & Working Philosophy

> **Canonical operating model** for humans and AI agents.  
> **Last updated:** 2026-05-26  
> **Related:** [`PRIORITIES.md`](./PRIORITIES.md) · [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) · [`ARCHITECTURE.md`](../ARCHITECTURE.md) · [`ARCH_V2_VISION.md`](./ARCH_V2_VISION.md)

---

## What we are building

**F3Next** is an autonomous ERP deployment and operations platform: ingest messy company data, map it to ERPNext, deploy the site, import in phases, then let users operate ERP via natural language.

**Near-term (v1.5 → Green Surface beta):** any Green Surface–class upload → correct doctype map → honest validate UI → safe live import on `{slug}.f3next.in`.

**Long-term (v2):** reasoning agent with live schema, tools, and feedback loops — scalable by **data**, not code edits. See [`ARCH_V2_VISION.md`](./ARCH_V2_VISION.md). Do not start full v2 until beta gate passes.

---

## Foundation stack (L0–L5)

Build order matters. A fix that skips a lower layer is a patch; a fix that strengthens a layer is foundation work.

| Layer | Name | Owns |
|-------|------|------|
| **L0** | Shared Platform | `shared_llm`, `llm_router`, Temporal, worker deploy parity, Supabase session state |
| **L1** | Honesty Contracts | `stage` vs `session.status`, validate pass/partial/fail, import phase errors vs `complete`, import-results API |
| **L2** | Corpus Spine | `corpus_merge.py`, classify → map → validate → finalize plan |
| **L3** | ERP Knowledge | KB mapping modules, baseline seed, SchemaResolver v1 bridge |
| **L4** | Import Execution | phased import, site prerequisites order, `import_idempotency` |
| **L5** | Observability UX | chat bar, import results panel, classification transparency |

**IS ten pillars** ([`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md)) map onto L2–L4. When triaging, name the pillar number (1–10), not just the file that threw the error.

---

## Failure taxonomy (classify before code)

Every issue gets a **class** and **pillar** before a PR:

| Class | Meaning | Response |
|-------|---------|----------|
| **A — Code bug** | Wrong order, wrong branch, UI lies about backend | Structural fix at the owning layer |
| **B — KB / pillar gap** | Missing synonym, mapping module, validation rule | Extend KB or `validation_rules.json`; promote from golden matrix |
| **C — Pillar not built** | Needs SchemaResolver, ValidationReport, corpus doc | Schedule Tier 7 bridge item; no filename one-off |
| **D — Ops / env** | Stale worker, missing deps, manual ERP setup | Deploy/rebuild/smoke; document in runbook |

**Rule:** No PR without `(class, pillar, layer)` in description or backlog line.

---

## Working philosophy

### Architecture over patches

**Prefer:**
- One policy in `corpus_merge.py` over per-file hacks in activities
- `validation_rules.json` over hardcoded fallbacks in validation agent
- Workflow honesty over UI greenwashing
- Baseline seed **before** Company create over manual ERPNext wizard workarounds

**Reject:**
- Filename-only priors without KB promotion path
- UI showing `complete` when `execute_import_phase` returns `steps_failed > 0`
- Fixing IS classification without checking shared LLM / OS smoke

### Speed = narrow WIP + gates

- Max **5 active items** in [`PRIORITIES.md`](./PRIORITIES.md)
- **Golden run** is the integration test — [`GREEN_SURFACE_GOLDEN_MATRIX.md`](../containers/implementation/dev_fixtures/GREEN_SURFACE_GOLDEN_MATRIX.md)
- **OS smoke after any L0 LLM change:** `python -m shared.smoke_llm`
- Re-prioritize after each golden run

### Honesty is a feature

- Validate: pass / partial / fail (not binary green)
- Import: per-doctype success/fail via `GET /api/implementation/import-results/{project_id}`
- Workflow: `complete_with_errors` when import phases partially fail

---

## Agent decision checklist

Run before every solution:

1. **Restate the symptom** in user terms.
2. **Identify layer** L0–L5 and **IS pillar** 1–10.
3. **Classify** A / B / C / D.
4. **Check cross-cutting impact:** OS, shared LLM, both workers?
5. **Choose fix type:** structural (preferred) · KB data (promoted) · patch (discouraged)
6. **Define verify:** unit test, harness step, or golden checklist row.
7. **Update backlog** in IS_V2_BACKLOG or PRIORITIES before merge.

If two fix types compete, choose the one that **reduces future patch surface**.

---

## Closure sprint (current focus)

Foundation v1.0.0 **code complete** — automated verify:

```bash
python scripts/verify_foundation.py
```

Manual golden + worker deploy before `v1.0.0-rc`: [`docs/v1.0.0/FOUNDATION_VERIFICATION.md`](v1.0.0/FOUNDATION_VERIFICATION.md)

| # | Item | Layer | Status |
|---|------|-------|--------|
| 1 | Baseline seed before `ensure_site_prerequisites` | L4 | **done** |
| 2 | Workflow `complete_with_errors` when `steps_failed > 0` | L1 | **done** |
| 3 | ImportView wired to import-results API | L5 | **done** |
| 4 | Shared LLM deps pinned across IS + OS workers | L0 | **done** |
| 5 | Re-finalize API + foundation unit suite | L2 | **done in repo** |
| 6 | Green Surface golden re-run + beta report | Gate | **manual** — see FOUNDATION_VERIFICATION.md |

**Next after rc tag:** Tier 3 IS chat bar ([`PRIORITIES.md`](PRIORITIES.md)); Tier 7 universal IS is post-beta.

---

## KB promotion (branch 04 policy spine)

When a production or golden incident reveals a rule:

1. Add `rule_id` + message to `containers/knowledge_base/erpnext/schema/` (`validation_rules.json`, `execution_preflight_rules.json`, or `os_validation.json`).
2. Wire loader in `shared/kb/` if new file type.
3. Add unit test in `shared/tests/test_kb_policy.py` or golden anchor in `test_golden_matrix_contracts.py`.
4. Run `python scripts/sync_autofill_from_kb.py` if `erp_autofill_fields` changed.

No filename-only priors without this path.

**Exit criteria:** Green Surface loop completes OR beta report with classified failures; OS/LLM smoke green; no lying `complete` stage.

---

## Freeze rules (until beta report signed off)

**Allowed:** P0 blockers, L0 deploy fixes, honesty contracts, KB promotions from golden matrix, docs

**Frozen:** New filename priors, one-off activity branches, sandbox terminology, multi-agent experiments (P4)

**Requires approval:** Any PR touching classify + map + validate + import in one change

---

## v1.5 vs v2 tagging

- **v1.5 hardening** — strengthens deterministic pipeline (Tier 7 bridge, corpus policy, ValidationReport)
- **v2 agentic** — live tool-calling agent replaces a pipeline node; defer until beta

Example: adding `Project.json` to KB = v1.5. pgvector-primary classifier = v2.

---

## Re-finalize stale import plans

When worker/KB fixes change plan logic but DB still holds an old blocked plan:

```bash
# Option A — API (preferred)
curl -X POST "$BASE/api/implementation/re-finalize-plan/{project_id}"

# Option B — harness (local / SSH on worker host)
python -m containers.implementation.is_harness --step finalize_import_plan
# Update session_id in containers/implementation/dev_fixtures/finalize_import_plan.json first
```

---

## Success metrics

1. **Trust:** Validate and import UI match backend truth
2. **Throughput:** One golden run per deploy; failures logged with class + pillar
3. **Stability:** IS + OS workers share working LLM layer
4. **Velocity:** Focus list ≤5 items; zero untagged patches merged
