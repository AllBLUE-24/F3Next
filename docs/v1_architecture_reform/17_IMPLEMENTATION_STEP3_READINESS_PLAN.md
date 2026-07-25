# Implementation Step 3 — Gap Analysis & Readiness

Formal plan for productizing Analyze-phase readiness (IS pillar 8).

## Architecture triage

| Field | Value |
|-------|--------|
| **Layer** | L2 Corpus spine → L3 ERP knowledge |
| **IS pillar** | **8** — Gap analysis & supervisor |
| **Classification** | **C** — pillar extension |
| **Product UI** | Analyze (`StepRail.tsx`) |
| **Boundary** | Step 3 = "Do we have the data?" — not mapping/validation (Step 4) |

## Package

Primary code: [`containers/implementation/readiness/`](../../containers/implementation/readiness/)

Backward-compat shims: [`data_readiness_agent/__init__.py`](../../containers/implementation/data_readiness_agent/__init__.py)

## Phased rollout

| Phase | Goal | Status |
|-------|------|--------|
| **A** | Package + `resolve_required_fields` + contracts | ✅ Done |
| **B** | `build_readiness_matrix()` offline | ✅ Done |
| **C** | Gaps + GREEN/YELLOW/RED gate | ✅ Done |
| **D** | API + workflow thin wiring | ✅ Done |
| **E** | Analyze matrix UI | ✅ Done |
| **F** | Harness + golden gate on `3rd_run` | ✅ Harness ready |

## Required-field policy

1. Doctypes from Discovery `seed_doctypes` (never expand from corpus alone).
2. Fields: **live Frappe first** via `mapping_agent/live_schema.py` when `deployment_details` exist.
3. Bridge: graph → KB → fallback via `is_common/required_fields.py`.
4. Intersect with F3iche `import_field_policy`; subtract `default_when_missing`.
5. Compare corpus **columns** to required fieldnames (not cell-level type checks — Step 4).

## Verification

```bash
pytest containers/implementation/readiness/test/ -q
python -m containers.implementation.readiness.test.harness_readiness --matrix
python -m containers.implementation.readiness.test.harness_readiness --fixture green_surface_3rd_run
```

## v1-worthy definition

1. Every confirmed MVP seed doctype appears in readiness matrix with required vs present fields.
2. Required fields resolved live-first when credentials exist; honest bridge otherwise.
3. Missing doctypes and critical missing fields produce actionable supervisor questions.
4. Gap upload re-runs Step 2 partial pipeline and re-assesses (Phase D).
5. `readiness_level` gates Step 4; no false GREEN.
6. Golden `3rd_run` passes offline harness (matrix stability + ready count).

## Sprint order (remaining)

1. Phase D — API + workflow thin wiring
2. Phase E — Analyze matrix UI + honesty layer

See also: [`readiness/README.md`](../../containers/implementation/readiness/README.md)
