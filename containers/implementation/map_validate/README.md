# Step 4 — Map & Validate



Implementation Step 4 of the v1 pipeline (Step 3 = `readiness/`, Step 5 = import).



## Phased rollout



| Phase | Goal | Status |

|-------|------|--------|

| **A** | Package + models + inputs | ✅ Done |

| **B** | `assess_map_validate_offline()` + gate | ✅ Done |

| **C** | `validate_ui.py` | ✅ Done |

| **D** | API + launcher hook | ✅ Done |

| **E** | ValidateSummaryBanner | ✅ Done |

| **F** | Harness + 3rd_run tests | ✅ Done |



## Commands



```bash

pytest containers/implementation/map_validate/test/ -q

python -m containers.implementation.map_validate.test.harness_map_validate --matrix

python -m containers.implementation.map_validate.test.harness_map_validate --fixture green_surface_3rd_run

```



## v1-worthy definition



1. Honest pass/partial/fail on mapped payloads.

2. `import_ready` false when blocking errors or critical unmapped seeds.

3. Golden `3rd_run` offline: party + SO + PO map pass; validate not fail.

4. UI banner strips internal pipeline jargon.

5. Wraps existing `mapping_agent` + `validation_agent` — no rewrite.
