"""Archetype registry — single KB→code bridge for Discovery scoping and LLM hints."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DISCOVERY_KB = Path(__file__).resolve().parent / "kb"
_CATALOG_PATH = _DISCOVERY_KB / "archetype_catalog.json"
_F3ICHE_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "common" / "f3iches"
_GRAPH_PATH = (
    Path(__file__).resolve().parent.parent
    / "knowledge_base"
    / "erpnext"
    / "erpnext_doctype_graph.json"
)

_SIGNAL_MIN_SCORE = 1

# ERPNext doctypes valid for graph extension when not yet in erpnext_doctype_graph.json
_GRAPH_EXTENSION_ALLOWLIST = frozenset({
    "Issue",
    "Maintenance Visit",
    "Maintenance Schedule",
    "Warranty Claim",
    "Serial No",
    "Asset",
    "Asset Movement",
    "Asset Repair",
    "Asset Category",
    "Employee",
    "Landed Cost Voucher",
    "Subcontracting Order",
    "Subcontracting Receipt",
    "Supplier",
    "Purchase Order",
    "Purchase Receipt",
    "Material Request",
    "Workstation",
    "Downtime Entry",
    "Routing",
    "Operation",
    "Price List",
    "UOM",
    "Stock Reconciliation",
    "Warehouse",
    "Debit Note",
    "Credit Note",
    "Sales Partner",
    "Address",
    "Pricing Rule",
    "Currency Exchange",
})


@lru_cache(maxsize=1)
def _load_doctype_graph_keys() -> frozenset[str]:
    if not _GRAPH_PATH.is_file():
        return frozenset()
    try:
        with open(_GRAPH_PATH, encoding="utf-8") as f:
            graph = json.load(f)
        return frozenset((graph.get("doctypes") or {}).keys())
    except Exception as e:
        logger.warning("Failed to load doctype graph for archetype registry: %s", e)
        return frozenset()


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    """Load global archetype catalog."""
    if not _CATALOG_PATH.is_file():
        return {"archetypes": [], "_source": "missing"}
    try:
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("archetypes"), list):
            return data
    except Exception as e:
        logger.warning("Failed to load archetype catalog: %s", e)
    return {"archetypes": [], "_source": "error"}


def load_f3iche_archetypes(f3iche_id: Optional[str]) -> list[dict[str, Any]]:
    """Load bottlenecks[] from a F3iche JSON."""
    if not f3iche_id:
        return []
    path = _F3ICHE_DIR / f"{f3iche_id}.json"
    if not path.is_file():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("bottlenecks")
        if not isinstance(raw, list):
            return []
        return [b for b in raw if isinstance(b, dict) and b.get("archetype_id")]
    except Exception as e:
        logger.debug("No bottlenecks[] for %s: %s", f3iche_id, e)
        return []


def merged_archetypes(f3iche_id: Optional[str] = None) -> list[dict[str, Any]]:
    """
    F3iche bottlenecks override catalog entries with the same archetype_id.
    Order: f3iche entries first, then catalog-only entries.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for entry in load_catalog().get("archetypes") or []:
        aid = str(entry.get("archetype_id") or "").strip()
        if aid:
            by_id[aid] = dict(entry)
    for entry in load_f3iche_archetypes(f3iche_id):
        aid = str(entry.get("archetype_id") or "").strip()
        if aid:
            by_id[aid] = dict(entry)
    return list(by_id.values())


def list_archetype_ids(f3iche_id: Optional[str] = None) -> list[str]:
    return sorted(
        str(a.get("archetype_id") or "").strip()
        for a in merged_archetypes(f3iche_id)
        if a.get("archetype_id")
    )


def get_by_id(archetype_id: Optional[str], f3iche_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Return archetype dict for id, or None."""
    aid = str(archetype_id or "").strip()
    if not aid:
        return None
    for entry in merged_archetypes(f3iche_id):
        if str(entry.get("archetype_id") or "").strip() == aid:
            return entry
    return None


def _signal_score(text: str, signals: list[str]) -> int:
    if not text or not signals:
        return 0
    haystack = text.lower()
    score = 0
    for signal in signals:
        sig = str(signal or "").strip().lower()
        if not sig:
            continue
        if sig in haystack:
            score += 1
            continue
        if len(sig) > 4 and re.search(re.escape(sig), haystack, re.I):
            score += 1
    return score


def match_by_signals(
    text: str,
    f3iche_id: Optional[str] = None,
    *,
    min_score: int = _SIGNAL_MIN_SCORE,
    top_k: int = 1,
) -> list[tuple[dict[str, Any], int]]:
    """
    Score archetypes by signal hits in text.
    Returns [(archetype, score), ...] sorted by score desc.
    """
    if not text.strip():
        return []
    ranked: list[tuple[dict[str, Any], int]] = []
    for entry in merged_archetypes(f3iche_id):
        signals = entry.get("signals") or []
        score = _signal_score(text, signals)
        if score >= min_score:
            ranked.append((entry, score))
    ranked.sort(key=lambda x: (-x[1], str(x[0].get("archetype_id") or "")))
    return ranked[:top_k]


def best_signal_match(
    text: str,
    f3iche_id: Optional[str] = None,
    *,
    min_score: int = _SIGNAL_MIN_SCORE,
) -> Optional[tuple[dict[str, Any], int]]:
    matches = match_by_signals(text, f3iche_id, min_score=min_score, top_k=1)
    return matches[0] if matches else None


def score_archetype_signals(
    archetype_id: Optional[str],
    text: str,
    f3iche_id: Optional[str] = None,
) -> int:
    """Signal hit count for one archetype id in text (0 if unknown or no hits)."""
    entry = get_by_id(archetype_id, f3iche_id)
    if not entry:
        return 0
    return _signal_score(text, entry.get("signals") or [])


def signal_match_rankings(
    text: str,
    f3iche_id: Optional[str] = None,
    *,
    top_k: int = 5,
    min_score: int = _SIGNAL_MIN_SCORE,
) -> list[dict[str, Any]]:
    """
    Top archetype ids by signal score for observability (shadow ranking).

    Returns [{"archetype_id": str, "score": int}, ...] sorted by score desc.
    """
    ranked = match_by_signals(text, f3iche_id, min_score=min_score, top_k=top_k)
    return [
        {
            "archetype_id": str(entry.get("archetype_id") or ""),
            "score": score,
        }
        for entry, score in ranked
        if entry.get("archetype_id")
    ]


def build_routing_diagnostics(
    *,
    context_text: str,
    f3iche_id: Optional[str],
    llm_archetype_id: Optional[str],
    chosen_archetype_id: Optional[str],
    archetype_source: Optional[str],
    top_k: int = 5,
    mismatch_margin: int = 2,
) -> dict[str, Any]:
    """
    Shadow signal diagnostics for mvp_boundary (Phase 1 observability).

    Does not change which archetype is selected — reporting only.
    """
    candidates = signal_match_rankings(context_text, f3iche_id, top_k=top_k)
    llm_id = str(llm_archetype_id or "").strip().lower()
    if llm_id in ("null", "none", "undefined"):
        llm_id = ""

    llm_score = score_archetype_signals(llm_id, context_text, f3iche_id) if llm_id else 0
    top_id = candidates[0]["archetype_id"] if candidates else None
    top_score = candidates[0]["score"] if candidates else 0

    mismatch = False
    note: str | None = None
    if (
        archetype_source == "mvp_focus"
        and llm_id
        and top_id
        and llm_id != top_id
        and top_score - llm_score >= mismatch_margin
    ):
        mismatch = True
        note = (
            f"LLM picked {llm_id!r} (signal score {llm_score}); "
            f"top signal match is {top_id!r} (score {top_score})"
        )

    chosen_score = (
        score_archetype_signals(chosen_archetype_id, context_text, f3iche_id)
        if chosen_archetype_id
        else 0
    )

    return {
        "signal_match_candidates": candidates,
        "llm_archetype_id": llm_id or None,
        "llm_archetype_signal_score": llm_score if llm_id else None,
        "chosen_archetype_signal_score": chosen_score if chosen_archetype_id else None,
        "archetype_routing_mismatch": mismatch,
        "archetype_routing_note": note,
    }


def canonicalize_seed(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    return raw.split(" (")[0].strip()


def resolve_seed_doctypes(
    archetype: dict[str, Any],
    template_seeds: list[str],
    *,
    allow_graph_extension: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Resolve day1_seed_hints against template and optional graph.

    Returns (resolved_seeds, graph_extensions) where graph_extensions are hints
    included via erpnext_doctype_graph but not in template_seeds.
    """
    template_set = set(template_seeds)
    graph_keys = _load_doctype_graph_keys() if allow_graph_extension else frozenset()
    extension_keys = graph_keys | (_GRAPH_EXTENSION_ALLOWLIST if allow_graph_extension else frozenset())

    resolved: list[str] = []
    graph_extensions: list[str] = []

    for hint in archetype.get("day1_seed_hints") or []:
        dt = canonicalize_seed(str(hint))
        if not dt:
            continue
        if dt in template_set:
            if dt not in resolved:
                resolved.append(dt)
        elif allow_graph_extension and dt in extension_keys:
            if dt not in resolved:
                resolved.append(dt)
                if dt not in template_set:
                    graph_extensions.append(dt)
        else:
            logger.debug(
                "Archetype %s hint %s not in template or graph",
                archetype.get("archetype_id"),
                dt,
            )

    defer = {
        canonicalize_seed(str(d))
        for d in (archetype.get("defer_typically") or [])
        if d
    }
    resolved = [d for d in resolved if d not in defer]
    return resolved, graph_extensions


_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_archetype_entry(
    entry: dict[str, Any],
    *,
    source: str,
    graph_keys: frozenset[str],
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single archetype row."""
    errors: list[str] = []
    warnings: list[str] = []
    aid = str(entry.get("archetype_id") or "").strip()

    if not aid:
        errors.append(f"{source}: missing archetype_id")
        return errors, warnings
    if not _ID_PATTERN.match(aid):
        errors.append(f"{source}: archetype_id {aid!r} must be snake_case")

    if not str(entry.get("primary_bottleneck") or "").strip():
        warnings.append(f"{source} {aid}: missing primary_bottleneck")

    signals = entry.get("signals") or []
    if not signals:
        warnings.append(f"{source} {aid}: no signals[] (signal-match fallback weak)")
    elif len(signals) < 3:
        warnings.append(f"{source} {aid}: fewer than 3 signals")

    hints = entry.get("day1_seed_hints") or entry.get("suggested_seed_doctypes") or []
    if not hints:
        errors.append(f"{source} {aid}: no day1_seed_hints")
    else:
        for hint in hints:
            dt = canonicalize_seed(str(hint))
            if not dt:
                continue
            if graph_keys and dt not in graph_keys:
                warnings.append(
                    f"{source} {aid}: day1_seed_hint {dt!r} not in erpnext_doctype_graph"
                )

    return errors, warnings


def validate_archetype_registry(
    f3iche_id: Optional[str] = None,
    *,
    check_all_f3iches: bool = False,
) -> dict[str, Any]:
    """
    Validate catalog + optional F3iche bottlenecks[] for Research merge gates.

    Returns {"errors": [...], "warnings": [...], "archetype_count": int}.
    """
    errors: list[str] = []
    warnings: list[str] = []
    graph_keys = _load_doctype_graph_keys()
    seen_ids: dict[str, str] = {}

    catalog = load_catalog()
    for idx, entry in enumerate(catalog.get("archetypes") or []):
        if not isinstance(entry, dict):
            errors.append(f"catalog entry[{idx}] is not an object")
            continue
        source = f"catalog[{entry.get('archetype_id') or idx}]"
        aid = str(entry.get("archetype_id") or "").strip()
        if aid:
            if aid in seen_ids:
                errors.append(f"duplicate archetype_id {aid!r} ({seen_ids[aid]} vs {source})")
            else:
                seen_ids[aid] = source
        entry_errors, entry_warnings = _validate_archetype_entry(
            entry, source=source, graph_keys=graph_keys
        )
        errors.extend(entry_errors)
        warnings.extend(entry_warnings)

    f3iche_ids: list[Optional[str]]
    if check_all_f3iches:
        f3iche_ids = [
            p.stem for p in sorted(_F3ICHE_DIR.glob("*.json")) if not p.name.startswith("_")
        ]
    elif f3iche_id:
        f3iche_ids = [f3iche_id]
    else:
        f3iche_ids = []

    for fid in f3iche_ids:
        f3iche_seen: set[str] = set()
        for idx, entry in enumerate(load_f3iche_archetypes(fid)):
            if not isinstance(entry, dict):
                errors.append(f"f3iche {fid} bottlenecks[{idx}] is not an object")
                continue
            source = f"f3iche:{fid}[{entry.get('archetype_id') or idx}]"
            aid = str(entry.get("archetype_id") or "").strip()
            if aid:
                if aid in f3iche_seen:
                    errors.append(f"duplicate archetype_id {aid!r} within f3iche {fid}")
                f3iche_seen.add(aid)
            entry_errors, entry_warnings = _validate_archetype_entry(
                entry, source=source, graph_keys=graph_keys
            )
            errors.extend(entry_errors)
            warnings.extend(entry_warnings)

    merged_count = len(merged_archetypes(f3iche_id))
    return {
        "errors": errors,
        "warnings": warnings,
        "archetype_count": merged_count,
    }


def validate_archetype_load(f3iche_id: Optional[str] = None) -> list[str]:
    """Return warning strings for archetypes missing day1_seed_hints (legacy helper)."""
    result = validate_archetype_registry(f3iche_id)
    return [w for w in result["warnings"] if "day1_seed_hints" in w or "no day1" in w]
