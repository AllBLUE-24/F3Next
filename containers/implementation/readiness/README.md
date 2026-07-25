# Step 3 — Readiness (gap analysis · matrix · gate)



Implementation Step 3 of the v1 pipeline (Step 1 = `containers/discovery/`, Step 2 = `corpus/`).



## Phased rollout



| Phase | Goal | Status |

|-------|------|--------|

| **A** | Package + `resolve_required_fields` + contracts | ✅ Done |

| **B** | `build_readiness_matrix()` offline | ✅ Done |

| **C** | Gaps + GREEN/YELLOW/RED gate | ✅ Done |

| **D** | API + workflow thin wiring | ✅ Done |

| **E** | Analyze matrix UI | ✅ Done |

| **F** | Harness + golden gate on `3rd_run` | ✅ Harness ready |



## Environment flags



| Variable | Default | Purpose |

|----------|---------|---------|

| `READINESS_REQUIRE_DISCOVERY` | `true` | Fail assess when `seed_doctypes` missing |

| `READINESS_LIVE_SCHEMA_PRIMARY` | `true` | Prefer live ERP schema when `deployment_details` exist |



## Commands



```bash

pytest containers/implementation/readiness/test/ -q

python -m containers.implementation.readiness.test.harness_readiness --matrix

python -m containers.implementation.readiness.test.harness_readiness --fixture green_surface_3rd_run

```



## V1-worthy definition (Step 3)



1. Every confirmed MVP seed doctype appears in the readiness matrix with required vs present fields.

2. Required fields resolved **live-first** when deployment credentials exist; honest bridge otherwise.

3. Missing doctypes and critical missing fields produce actionable supervisor questions.

4. `readiness_level` gates Step 4; no false GREEN.

5. Golden `3rd_run` passes offline harness.
