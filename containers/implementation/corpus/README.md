# Step 2 — Corpus (upload · parse · understand)

Implementation Step 2 of the v1 pipeline (Step 1 = `containers/discovery/`).

## Phased rollout

| Phase | Goal | Status |
|-------|------|--------|
| **0** | Baseline + deterministic checkers | ✅ Done |
| **1** | Package restructure (`corpus/`), backward-compat shims | ✅ Done |
| **2** | Discovery context mandatory in enrich; gate on manifest | ✅ Done |
| **3** | Live LLM golden matrix (fixtures + `--live-llm`) | ✅ Harness ready |
| **4** | Workflow Step 2/5 banners; corpus-first doctype assignment | ✅ Done |

## Environment flags

| Variable | Default | Purpose |
|----------|---------|---------|
| `CORPUS_REQUIRE_DISCOVERY` | `true` | Fail enrich if no discovery transcript/metadata |
| `CORPUS_ALLOW_DEFAULTS` | `false` | Set `true` to bypass discovery requirement (dev only) |
| `CORPUS_USE_LEGACY_CLASSIFIER` | `false` | Set `true` to use filename_priors/classifier in assign step |

## V1-worthy definition (Step 2)

1. Every parseable upload → manifest v2 with `file_meta` (columns, samples).
2. LLM corpus understanding attached to manifest (no patch KB on happy path).
3. Discovery context required before LLM enrich (unless `CORPUS_ALLOW_DEFAULTS=true`).
4. Explicit `gate_passed` from checkers on enrich result.
5. `assign_corpus_doctypes` prefers corpus understanding when `CORPUS_USE_LEGACY_CLASSIFIER=false`.

## Commands

```bash
# Unit tests (offline)
pytest containers/implementation/corpus/test/ -q

# Offline golden matrix
python -m containers.implementation.corpus.test.harness_corpus --matrix

# Single fixture
python -m containers.implementation.corpus.test.harness_corpus --fixture green_surface

# Live LLM matrix (requires API keys)
python -m containers.implementation.corpus.test.harness_corpus --matrix --live-llm
```
