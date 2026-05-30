# Branch 01 — `foundation/shared-platform`

> **Base:** `main`  
> **Merges into:** `foundation/os-brain` (required first)  
> **Layer focus:** L0–L3  
> **IS pillar:** 3 (KB), 6 (schema bridge)  
> **Class:** Mostly **C** (new platform modules) with some **A** (contract enforcement)

---

## 1. Branch thesis

Extract **Company Brain primitives** into `shared/` so IS and OS import the same code paths. No Temporal workflow edits on this branch — only libraries, types, thin ERP tool wrappers, and tests.

**Outcome:** `from shared.entity_resolution import resolve_links_for_command` works in a unit test without starting workers.

---

## 2. Problems this branch solves

| Symptom | Root cause |
|---------|------------|
| OS asks “does customer exist?” via CVS | `BulkLinkResolver` only wired in IS import preflight |
| Duplicate link-fuzzy logic in OS planner vs validator | No shared resolution API |
| `os_field_semantics` OS-specific name | IS needs same title/company policies |
| No stable shape for gate outputs | UI and activities invent ad hoc dicts |

---

## 3. Deliverables (file-level)

### 3.1 New package: `shared/entity_resolution/`

| File | Responsibility |
|------|----------------|
| `__init__.py` | Public API exports |
| `ler.py` | Wrap `BulkLinkResolver`: `build_link_cache(adapter, targets) -> dict[str, list[str]]` |
| `targets.py` | `collect_link_targets_from_intent(intent, doctype, kb_schema)` — mirror IS row collector for OS |
| `resolve.py` | `resolve_entities_batch(raw_entities, link_cache) -> ResolvedEntities` |
| `gaps.py` | `resolution_gaps_from_unresolved(...) -> list[GapItem]` |

**Reuse:** [`shared/erp_adapters/link_resolver.py`](../../shared/erp_adapters/link_resolver.py) — do not fork matching logic.

### 3.2 Gate contracts: `shared/gate_contracts.py`

TypedDicts / dataclasses:

- `GateName`, `GateStatus`, `GapItem`, `HonestySlice`, `GateResult`  
- `gap_to_clarification_question(gap) -> str` (optional helper)

Used by OS activities first; IS activities adopt in branch 03.

### 3.3 Semantics rename / alias

| Action | Path |
|--------|------|
| Create | `shared/erp_semantics.py` — move or re-export from `os_field_semantics.py` |
| Keep shim | `shared/os_field_semantics.py` → `from shared.erp_semantics import *` (deprecation comment) |

Functions to consolidate (already exist in OS path):

- `business_fields_missing`  
- `merge_clarification_into_intent`  
- `preserve_transaction_entities`  
- `apply_profile_autofill_to_payload`  
- `apply_computed_defaults_to_payload`  
- `build_transaction_title`  
- `resolve_company_for_payload`  
- `resolve_link_value_from_options`  
- `is_master_create_doctype`

### 3.4 ERP tools (LER-backed): `shared/erp_tools/`

| Tool function | Used by (later branches) |
|---------------|--------------------------|
| `list_master(adapter, doctype, query?, limit?)` | Clarity T3, IS classifier |
| `get_item_flags(adapter, item_code)` | OS execution preflight |
| `get_supplier_flags(adapter, supplier)` | OS execution preflight |

Implementation: thin wrappers over `ERPNextAdapter.list_records` / `get_doc` — no LLM.

### 3.5 Context snapshot extension (types only)

Document expected keys in `context_snapshots` JSON (implementation in os-brain):

```python
{
  "link_cache": {"Customer": ["CUST-001", ...], "Company": ["Regww Pvt Ltd"]},
  "resolved_entities": {"customer": "CUST-001", "items": [...]},
  "resolution_gaps": [],
  "live_fetched_at": "ISO8601",
  "brain_version": "1.0.0"
}
```

### 3.6 Tests

| File | Covers |
|------|--------|
| `shared/tests/test_entity_resolution.py` | Suffix match, ambiguous pick, company list |
| `shared/tests/test_gate_contracts.py` | Serialization round-trip |
| `shared/tests/test_erp_semantics.py` | Port from `containers/os/tests/test_business_fields.py` critical cases |

---

## 4. Design decisions (ideation)

### 4.1 `link_cache` shape

- Key = ERP doctype string (`Customer`, `Item`, `Company`, …).  
- Value = ordered list of canonical `name` values from **one** `list_records` per doctype per command.  
- Optional: `link_cache_meta[doctype] = {fetched_at, count, truncated}`.

### 4.2 Resolution gap severity

| Severity | Meaning |
|----------|---------|
| `blocking` | Cannot plan payload |
| `choice` | Multiple candidates; CLARIFY with list |
| `hint` | CVS suggested zero; live has candidates — still `choice` |

### 4.3 Brain version string

Bump `brain_version` in snapshot when LER algorithm or KB policy version changes — aids debugging pilot tenants.

---

## 5. Explicit non-goals (this branch)

- Wiring `resolve_entities` into Temporal workflow.  
- Changing validator or clarity activities.  
- IS readiness refactor.  
- Frontend changes.

---

## 6. Dependencies & interfaces for downstream branches

**Exports OS brain must use:**

```python
from shared.entity_resolution.ler import build_link_cache, apply_resolved_to_intent
from shared.gate_contracts import GateResult, GapItem
from shared.erp_semantics import apply_computed_defaults_to_payload, resolve_company_for_payload
```

**Exports IS brain must use:**

```python
from shared.entity_resolution.ler import build_link_cache  # same as import preflight today
from shared.gate_contracts import GateResult
```

Contract freeze: tag `shared-platform-v1` in PR description when merging to os-brain.

---

## 7. Verification

| Check | Command / action |
|-------|------------------|
| Unit tests | `pytest shared/tests/ -q` |
| Import smoke | `python -c "from shared.entity_resolution import build_link_cache"` |
| No worker required | CI job `shared-only` optional |
| Backward compat | Existing `test_business_fields.py` still passes via shim |

---

## 8. PR breakdown (suggested commits)

1. `gate_contracts.py` + tests  
2. `entity_resolution/` + tests  
3. `erp_semantics.py` + shim `os_field_semantics.py`  
4. `erp_tools/` + tests  
5. Docs: one paragraph in [`ARCH_CONTEXT_ENGINE.md`](../ARCH_CONTEXT_ENGINE.md) — LER overlay  

---

## 9. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports with `containers/os` | shared must not import containers |
| Divergence from IS `BulkLinkResolver` usage | Single `ler.py` wrapper called by both |
| Large move breaks open PRs | Shim re-exports for one sprint |

---

## 10. Success criteria (branch complete)

- [x] All §3 files exist with tests  
- [x] `BulkLinkResolver` called only through `shared/entity_resolution` in new code  
- [x] GateResult documented in [`OPERATING_MODEL.md`](./OPERATING_MODEL.md) matches implementation  
- [x] Downstream branch 02 can start without modifying shared API  

---

*Next: [`branch-02-foundation-os-brain.md`](./branch-02-foundation-os-brain.md)*
