# Phase 0: MVP Pipeline Foundation Fixes

> **Branch:** `feature/phase-0-mvp-pipeline-foundation`  
> **Started:** 2026-06-19  
> **Goal:** Fix critical architectural flaws blocking production-grade MVP boundary and gap detection

---

## Problem Statement

The Import Scope (IS) pipeline is not production-grade due to:

1. **Discovery chat context not flowing into F3iche synthesis** — user's stated bottleneck/business context ignored
2. **Gap detection runs before mapping** — column synonym brittleness causes false "missing data" errors
3. **Poor supervisor messaging** — generic "missing field X" without file/column context
4. **No corpus re-enrichment loop** — additional uploads don't trigger full re-analysis
5. **Hardcoded synonym dependency** — only 15 doctypes with KB coverage; no learning from mappings

---

## Phase 0 Scope (P0 Foundation Blockers)

### Fix 1: Integrate Discovery Chat into F3iche Synthesis ✓ VERIFIED
- **Layer:** L2 (Corpus Spine)
- **Pillar:** 3 (Intent & Classification)
- **Class:** A (code bug - wrong data flow)
- **Status:** ALREADY IMPLEMENTED - No changes needed

**Existing Implementation:**
- `synthesize_f3iche_confirmation` already calls `load_discovery_context()` 
- Discovery metadata + chat transcript flow into F3iche LLM prompt
- Synthesis merges: file inference + discovery chat + corpus summary

---

### Fix 2: Move Gap Detection AFTER Mapping Attempt (PARTIALLY DEFERRED)
- **Layer:** L2-L3 (Corpus Spine + ERP Knowledge)
- **Pillar:** 8 (Gap Analysis & Supervisor)
- **Class:** A (architectural - wrong gate placement)
- **Status:** ROOT CAUSE IDENTIFIED - Full fix requires broader refactor

**Root Cause:**
- Step 8c `dry_run_map_file` uses only Tier 1+3 (KB exact + fuzzy), skips Tier 2 (LLM)
- False negatives when columns like `VendorID` need semantic mapping to `supplier_name`

**Phase 0 Action:**
- Enhanced gap messages with column context (Fix 3) mitigates user confusion
- Full resequencing deferred to P1 (requires workflow restructuring)

---

### Fix 3: Enrich Supervisor Messages with File + Column Context ✓ COMPLETED
- **Layer:** L5 (Observability UX)
- **Pillar:** 8 (Gap Analysis & Supervisor)
- **Class:** A (code bug - insufficient context in prompts)
- **Status:** IMPLEMENTED

**Changes:**
- [x] Extended `make_gap_item()` to accept column context params
- [x] Updated `gap_from_preflight_block()` to build rich questions with file/column details
- [x] Updated `gap_from_dry_run_failure()` to show successfully mapped columns
- [x] Enhanced supervisor validation messages to extract and present mapping audit trail
- [x] Gap messages now include:
  - Source file name
  - User's actual column names
  - Successfully mapped columns
  - Suggested working column names from KB

**Example Output:**
Before: "Missing required field: supplier_name"
After: "In file **vendors.csv**, we couldn't map these required fields: supplier_name. We successfully mapped: vendor_id, contact_name. Your columns: VendorID, Contact, Phone, Address. Try using column names like: supplier_name, supplier, vendor_name."

---

### Fix 4: Discovery Context in Corpus Understanding ✓ COMPLETED
- **Layer:** L2 (Corpus Spine)
- **Pillar:** 2 (Parse & Normalize Structure)
- **Class:** A (architectural - missing context)
- **Status:** IMPLEMENTED

**Changes:**
- [x] Added `discovery_chat_history` and `discovery_metadata` to `EnrichCorpusUnderstandingInput`
- [x] Created `_extract_discovery_context()` helper function
- [x] Updated `CORPUS_UNDERSTANDING_PROMPT` template with `{discovery_context}` section
- [x] Added `fetch_discovery_context()` helper in supervisor activities
- [x] Wired workflow to fetch discovery data before Step 2b and pass to corpus enrichment

**Verification:**
- Discovery bottleneck (e.g., "I track chemical batch compliance") now visible to corpus LLM
- Corpus classification considers business context when inferring doctypes

---

## Out of Scope (Deferred to P1/P2)

- Corpus re-enrichment loop (P1)
- Synonym KB growth from successful mappings (P2)
- SchemaResolver v1 for unknown doctypes (P2)

---

## Implementation Order

1. **Discovery → Corpus Understanding** (Fix 4) — foundational data flow
2. **Discovery → F3iche Synthesis** (Fix 1) — correct niche selection
3. **Gap Detection Resequencing** (Fix 2) — move after mapping
4. **Supervisor Message Enrichment** (Fix 3) — better UX

---

## Testing Strategy

- **Unit tests:** New functions for discovery context extraction
- **Golden matrix:** Green Surface 4th_run with modified discovery chat
- **Manual harness:** Test each step in isolation with discovery context

---

## Success Criteria

### Implemented (Phase 0)
1. ✓ Discovery chat context flows into corpus understanding LLM prompt
2. ✓ F3iche synthesis uses discovery metadata (already working)
3. ✓ Gap messages include file name, user columns, successfully mapped fields, and suggested alternatives
4. ✓ Supervisor messages are actionable with specific file/column context

### Deferred (P1)
1. Gap detection fully resequenced: file-level check in Step 8c, field-level after Step 9 mapping
2. Golden run: Green Surface 4th_run completes without false "missing data" errors from column name mismatch

---

## Related Docs

- [`FOUNDATIONS.md`](./FOUNDATIONS.md) — Layer L0-L5 architecture
- [`IS_V2_BACKLOG.md`](./IS_V2_BACKLOG.md) — 10 IS pillars + backlog
- [`NORTH_STAR.md`](./NORTH_STAR.md) — Agent shell vision
- [`PRIORITIES.md`](./PRIORITIES.md) — Current sprint items

---

## Change Log

| Date       | Engineer | Change                                    |
|------------|----------|-------------------------------------------|
| 2026-06-19 | AI Agent | Created Phase 0 tracking document         |
| 2026-06-19 | AI Agent | Implemented Fix 4: Discovery → Corpus     |
| 2026-06-19 | AI Agent | Verified Fix 1: Discovery → F3iche (already working) |
| 2026-06-19 | AI Agent | Diagnosed Fix 2: dry_run skips LLM tier   |
| 2026-06-19 | AI Agent | Implemented Fix 4: Discovery → Corpus (completed) |
| 2026-06-19 | AI Agent | Implemented Fix 3: Supervisor messages (completed) |
| 2026-06-19 | AI Agent | Ready for commit - Phase 0 core fixes done |

---

## Implementation Notes

### Fix 1 Status: ALREADY IMPLEMENTED ✓
The F3iche synthesis in `f3iche_confirmation_activities.py` already loads discovery context via `load_discovery_context()` and includes it in the synthesis LLM prompt. Discovery chat history and metadata flow correctly into F3iche selection.

### Fix 2 Root Cause IDENTIFIED
The `dry_run_map_file` in Step 8c uses only **Tier 1 (KB exact) + Tier 3 (KB fuzzy)** mapping, skipping **Tier 2 (LLM semantic mapping)**. This causes false negatives when user columns like `VendorID` need LLM intelligence to map to ERPNext `supplier_name`.

**Options:**
- A: Enable LLM in dry_run (add `IS_DRY_RUN_LLM=1` env var)
- B: Make Step 8c less strict (only check file-level coverage)
- C: Defer field-level gap reporting to Step 9 post-mapping

**Chosen:** Mix of B+C - Step 8c will report "file-level" gaps only, Step 9 will report field-level gaps after full mapping attempt.

### Fix 4 Status: IMPLEMENTED ✓
- Added `discovery_chat_history` and `discovery_metadata` params to `EnrichCorpusUnderstandingInput`
- Created `_extract_discovery_context()` helper in `enrich_corpus_understanding.py`
- Updated corpus understanding prompt template to include `{discovery_context}` placeholder
- Wired workflow to fetch discovery data from hooks table before Step 2b
- Discovery context now flows: hooks → workflow → corpus understanding → LLM prompt
