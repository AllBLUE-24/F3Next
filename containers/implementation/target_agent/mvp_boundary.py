"""MVP boundary and corpus-aware seed selection for Step 8."""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# Manufacturing doctypes deferred unless corpus/file evidence supports them.
_MANUFACTURING_SEEDS = frozenset({
    "Work Order", "BOM", "Job Card", "Batch", "Quality Inspection",
    "Quality Inspection Template",
})

# Deferred when LLM/f3iche suggests them but no file or corpus signal exists.
_OPTIONAL_WITHOUT_FILE_EVIDENCE = frozenset({
    "Item Variant", "Quotation", "Delivery Note", "Task", "Timesheet",
})

_PARTY_SEEDS = frozenset({"Customer", "Supplier"})

# Filename/corpus keyword hints when likely_erpnext_doctypes is empty.
_FILE_HINTS: List[Tuple[re.Pattern, List[str]]] = [
    (re.compile(r"purchase.?order|raw.?purchase|po[_\s-]", re.I), ["Purchase Order", "Supplier", "Item"]),
    (re.compile(r"client.?order|sales.?order|order", re.I), ["Sales Order", "Customer", "Project", "Item"]),
    (re.compile(r"partner|supplier|vendor|customer", re.I), ["Customer", "Supplier"]),
    (re.compile(r"project", re.I), ["Project"]),
    (re.compile(r"bom|recipe|formulation", re.I), ["BOM", "Item"]),
    (re.compile(r"work.?order|production", re.I), ["Work Order", "BOM"]),
    (re.compile(r"invoice", re.I), ["Sales Invoice", "Purchase Invoice"]),
    (re.compile(r"item|product|sku|material", re.I), ["Item"]),
]


def canonicalize_template_doctype(name: str) -> str:
    """Strip f3iche parenthetical labels: 'BOM (Formulation)' → 'BOM'."""
    raw = str(name or "").strip()
    if not raw:
        return ""
    return raw.split(" (")[0].strip()


def _iter_corpus_files(corpus_understanding: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not corpus_understanding:
        return []
    files = corpus_understanding.get("files") or []
    if isinstance(files, dict):
        return [{"filename": k, **(v if isinstance(v, dict) else {})} for k, v in files.items()]
    return [f for f in files if isinstance(f, dict)]


def seeds_from_corpus(
    corpus_understanding: Optional[Dict[str, Any]],
    *,
    canonicalize: Optional[Callable[[List[str]], List[str]]] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Deterministic seed doctypes from Step 2b corpus understanding.

    Returns (seed_doctypes, file_evidence).
    """
    seeds: Set[str] = set()
    evidence: List[Dict[str, Any]] = []

    for entry in _iter_corpus_files(corpus_understanding):
        fname = str(entry.get("filename") or entry.get("source_file") or "").strip()
        suggested: List[str] = []

        for dt in entry.get("likely_erpnext_doctypes") or []:
            dt_name = str(dt or "").strip()
            if dt_name:
                suggested.append(dt_name)

        if not suggested and fname:
            for pattern, hints in _FILE_HINTS:
                if pattern.search(fname):
                    suggested.extend(hints)
                    break

        suggested = list(dict.fromkeys(suggested))
        if suggested:
            for dt in suggested:
                seeds.add(dt)
            evidence.append({
                "file": fname,
                "corpus_role": entry.get("business_description") or "",
                "likely_entity_types": entry.get("likely_entity_types") or [],
                "suggested_seeds": suggested,
                "explicitly_not_doctypes": entry.get("explicitly_not_doctypes") or [],
            })

    seed_list = sorted(seeds)
    if canonicalize:
        seed_list = canonicalize(seed_list)
    return seed_list, evidence


def merge_seed_sources(*sources: List[str]) -> List[str]:
    """Union seed lists preserving first-seen order."""
    seen: Set[str] = set()
    merged: List[str] = []
    for source in sources:
        for dt in source or []:
            name = str(dt or "").strip()
            if name and name not in seen:
                seen.add(name)
                merged.append(name)
    return merged


def defer_without_evidence(
    seeds: List[str],
    corpus_seeds: List[str],
    file_evidence: List[Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    """
    Remove manufacturing seeds not supported by corpus/file evidence.

    Returns (active_seeds, deferred_doctypes).
    """
    corpus_set = set(corpus_seeds)
    active: List[str] = []
    deferred: List[str] = []

    for dt in seeds:
        if dt in _MANUFACTURING_SEEDS and dt not in corpus_set:
            # Also check if any file explicitly suggested this doctype
            has_file_signal = any(dt in (e.get("suggested_seeds") or []) for e in file_evidence)
            if not has_file_signal:
                deferred.append(dt)
                continue
        active.append(dt)

    return active, deferred


def refine_mvp_seeds(
    seeds: List[str],
    corpus_seeds: List[str],
    file_evidence: List[Dict[str, Any]],
    deferred: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """
    Post-filter MVP seeds:
      - Inject Customer/Supplier when party file evidence exists
      - Defer optional doctypes (Item Variant, Quotation, etc.) without corpus/file signal
    """
    corpus_set = set(corpus_seeds)
    evidence_seeds: Set[str] = set()
    has_party_file = False

    for entry in file_evidence or []:
        suggested = entry.get("suggested_seeds") or []
        evidence_seeds.update(suggested)
        if _PARTY_SEEDS & set(suggested):
            has_party_file = True
        fname = str(entry.get("file") or entry.get("filename") or "").lower()
        if not has_party_file and any(
            re.search(p, fname) for p in (r"partner", r"parties", r"vendor", r"customer")
        ):
            has_party_file = True
            evidence_seeds.update(_PARTY_SEEDS)

    active: List[str] = []
    extra_deferred: List[str] = list(deferred or [])

    for dt in seeds:
        if dt in _OPTIONAL_WITHOUT_FILE_EVIDENCE:
            if dt not in corpus_set and dt not in evidence_seeds:
                extra_deferred.append(dt)
                continue
        active.append(dt)

    if has_party_file:
        for dt in ("Customer", "Supplier"):
            if dt not in active:
                active.insert(0, dt)
                if dt in extra_deferred:
                    extra_deferred.remove(dt)

    return active, extra_deferred


def reconcile_setup_step_actions(
    setup_steps: List[Dict[str, Any]],
    seed_doctypes: List[str],
) -> List[Dict[str, Any]]:
    """
    Fix action inconsistencies — e.g. Work Order must_create requires BOM not optional.
    """
    seed_set = set(seed_doctypes)
    by_dt = {s["doctype"]: s for s in setup_steps if s.get("doctype")}

    wo = by_dt.get("Work Order")
    bom = by_dt.get("BOM")
    if (
        "Work Order" in seed_set
        and wo
        and wo.get("action") == "must_create"
        and bom
        and bom.get("action") == "optional_if_absent"
    ):
        bom["action"] = "must_create"

    if "BOM" in seed_set and bom and bom.get("action") == "optional_if_absent":
        bom["action"] = "must_create"

    return setup_steps


def load_f3iche_template_seeds(f3iche_path: str) -> Tuple[List[str], Dict[str, Any]]:
    """Load and canonicalize seed doctypes from f3iche JSON."""
    import json
    from pathlib import Path

    path = Path(f3iche_path)
    if not path.exists():
        return [], {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("required_doctypes") or data.get("mandatory_doctypes") or []
    seeds = [canonicalize_template_doctype(d) for d in raw if d]
    return list(dict.fromkeys(seeds)), data


def validation_rules_from_f3iche(f3iche_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract lightweight validation hints from f3iche template."""
    rules: Dict[str, Any] = {"custom_fields": [], "notes": []}
    masters = f3iche_data.get("erpnext_masters_setup") or {}
    item_struct = masters.get("item_structure") or {}
    custom = item_struct.get("custom_fields_required")
    if custom:
        rules["custom_fields"].append({"doctype": "Item", "fields": custom})
        rules["notes"].append("Item custom fields required per niche template")
    if f3iche_data.get("regulatory_criticality_level"):
        rules["regulatory_criticality"] = f3iche_data["regulatory_criticality_level"]
    return rules


def build_mvp_boundary(
    *,
    mode: str,
    source_mvp_focus: Optional[Dict[str, Any]],
    seed_doctypes_chosen: List[str],
    deferred_doctypes: List[str],
    file_evidence: List[Dict[str, Any]],
    corpus_summary: Optional[str],
    reasoning: str,
    profile_version: int = 1,
    synthesis_proposal: Optional[Dict[str, Any]] = None,
    discovery_alignment: Optional[Dict[str, Any]] = None,
    seeds_before_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assemble the mvp_boundary.json artifact."""
    return {
        "mode": mode,
        "source_mvp_focus": source_mvp_focus,
        "synthesis_proposal_ref": {
            "proposed_f3iche": (synthesis_proposal or {}).get("proposed_f3iche"),
            "alignment": (synthesis_proposal or {}).get("alignment"),
        } if synthesis_proposal else None,
        "discovery_alignment": discovery_alignment,
        "corpus_summary": corpus_summary,
        "file_evidence": file_evidence,
        "seeds_before_filter": seeds_before_filter or seed_doctypes_chosen,
        "seed_doctypes_chosen": seed_doctypes_chosen,
        "deferred_doctypes": deferred_doctypes,
        "reasoning": reasoning,
        "profile_version": profile_version,
    }
