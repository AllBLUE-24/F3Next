# Step 5 — Phased Import

Implementation Step 5 of the v1 pipeline (Step 4 = `map_validate/`).

## Phased rollout

| Phase | Goal | Status |
|-------|------|--------|
| **A** | Package + models + inputs | ✅ Done |
| **B** | `assess_import_offline()` + gate | ✅ Done |
| **C** | `import_ui.py` | ✅ Done |
| **D** | API + launcher hook | ✅ Done |
| **E** | ImportSummaryBanner | ✅ Done |
| **F** | Harness + golden gate on `3rd_run` | ✅ Done |

## Environment flags

| Variable | Default | Purpose |
|----------|---------|---------|
| `IMPORT_REQUIRE_MAP_VALIDATE` | `true` | Fail assess when Step 4 `import_ready=false` |
| `IMPORT_BLOCK_ON_VALIDATION_FAIL` | `true` | Plan blocked when validation level is fail |

## Commands

```bash
pytest containers/implementation/import_exec/test/ -q
python -m containers.implementation.import_exec.test.harness_import --matrix
python -m containers.implementation.import_exec.test.harness_import --fixture green_surface_3rd_run
```

## V1-worthy definition (Step 5)

1. Every mapped MVP seed doctype appears in the import plan with `action=create`.
2. Deferred doctypes produce `ready_with_gaps`, not false `blocked`.
3. Validation fail or Step 4 not import-ready → plan `blocked`.
4. Phase execution order matches dependency graph.
5. Golden `3rd_run` passes offline harness (plan not blocked, core create steps present).
