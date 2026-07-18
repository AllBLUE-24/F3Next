# Step 2 — Corpus (upload · parse · understand)

Implementation Step 2 of the v1 pipeline (Step 1 = `containers/discovery/`).

## Phased rollout

| Phase | Goal | Pass gate |
|-------|------|-----------|
| **0** | Baseline + deterministic checkers | `pytest containers/implementation/corpus/test/` green |
| **1** | Package restructure (`corpus/`), backward-compat shims | Existing IS tests still green |
| **2** | Discovery context mandatory in enrich; status handling hardened | Golden harness offline 10/10 |
| **3** | Live LLM golden matrix (Green Surface + variations) | `--live-llm` harness 10/10 |
| **4** | Workflow banners Step 2/5; retire legacy classifier on happy path | Feature flag off for priors |

## V1-worthy definition (Step 2)

1. Every parseable upload → manifest v2 with `file_meta` (columns, samples).
2. LLM corpus understanding attached to manifest (no `filename_priors` / patch KB).
3. Explicit `ok` \| `partial` \| `failed` status from checkers.
4. Golden fixtures pass offline gate before live LLM runs.

## Commands

```bash
# Unit tests (offline)
pytest containers/implementation/corpus/test/ -q

# Offline golden gate (fixtures only)
python -m containers.implementation.corpus.test.harness_corpus --fixture green_surface

# Live LLM (Phase 3+, requires credentials)
python -m containers.implementation.corpus.test.harness_corpus --fixture green_surface --live-llm
```
