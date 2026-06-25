"""Bulk link-field resolution for IS import pipeline."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from shared.erp_adapters.base import ERPAdapter

logger = logging.getLogger(__name__)

# Doctypes where ERPNext rejects disabled in list API queries.
_DOCTYPES_WITHOUT_DISABLED: frozenset[str] = frozenset({
    "BOM",
    "Company",
    "Customer Group",
    "Item Group",
    "Project",
    "Stock Entry Type",
    "Supplier Group",
    "Territory",
    "UOM",
})

# Link targets keyed by business id; ERPNext Link fields store document `name`.
_DOCTYPE_ALT_LOOKUP_FIELDS: dict[str, str] = {
    "Project": "project_name",
    "Customer": "customer_name",
    "Supplier": "supplier_name",
    "Item": "item_code",
}

# Common ERPNext warehouse abbreviations vs full names (Green Surface uses full names).
_BASE_ALIASES: dict[str, list[str]] = {
    "WIP": ["Work In Progress"],
    "Work In Progress": ["WIP"],
    "FG": ["Finished Goods"],
    "Finished Goods": ["FG"],
}


def _kb_uom_alias(val: str) -> Optional[str]:
    """Map common abbreviations (Ltr, gal) to ERPNext UOM names via KB parsing rules."""
    raw = str(val or "").strip()
    if not raw:
        return None
    try:
        from containers.os.payload_generator.kb_fields import field_kb

        normalized = field_kb().resolve_uom(raw)
        if normalized and normalized != raw:
            return normalized
    except Exception:
        pass
    return None


def _suffix_candidates(base: str, known_names: list[str]) -> list[str]:
    """Find ERPNext names matching base or known aliases, e.g. WIP -> Work In Progress - GS."""
    bases = [base]
    for alt in _BASE_ALIASES.get(base, []):
        if alt not in bases:
            bases.append(alt)
    seen: set[str] = set()
    candidates: list[str] = []
    for b in bases:
        for name in known_names:
            if name.startswith(f"{b} - ") and name not in seen:
                seen.add(name)
                candidates.append(name)
    return candidates


@dataclass
class ResolutionResult:
    """Result of resolving a single candidate value."""

    original: str
    resolved: Optional[str] = None
    ambiguous: bool = False
    ambiguous_candidates: list[str] = field(default_factory=list)


@dataclass
class ResolutionMap:
    """Bulk resolution outcome for linked doctypes."""

    resolved: dict[str, dict[str, str]] = field(default_factory=dict)
    """{target_doctype: {original_val: canonical_name}}"""
    unresolvable: dict[str, list[str]] = field(default_factory=dict)
    """{target_doctype: [values with zero matches]}"""
    ambiguous: dict[str, list[tuple[str, str, list[str]]]] = field(default_factory=dict)
    """{target_doctype: [(original, picked, all_candidates)]}"""

    def get_canonical(self, target_doctype: str, original_val: str) -> Optional[str]:
        mapping = self.resolved.get(target_doctype, {})
        if original_val in mapping:
            return mapping[original_val]
        return original_val if original_val not in self.unresolvable.get(target_doctype, []) else None


def resolve_single(
    val: str,
    known_names: list[str],
    preferred_abbr: Optional[str] = None,
) -> ResolutionResult:
    """
    Deterministic resolution of one candidate against known ERP names.

    Strategy order:
      1. Exact match
      2. Company-suffix match (ERPNext pattern: "WIP - GS")
      3. Prefer warehouse suffix matching live company abbr (GS CSV → REG site)
      4. Normalized case/space-insensitive match
    """
    val = val.strip()
    if not val:
        return ResolutionResult(original=val, resolved=None)

    known_set = set(known_names)

    if val in known_set:
        return ResolutionResult(original=val, resolved=val)

    if " - " in val:
        base = val.split(" - ")[0].strip()
        candidates = _suffix_candidates(base, known_names)
    else:
        candidates = _suffix_candidates(val, known_names)

    if len(candidates) == 1:
        return ResolutionResult(original=val, resolved=candidates[0])

    if len(candidates) > 1 and preferred_abbr:
        preferred = [c for c in candidates if c.endswith(f" - {preferred_abbr}")]
        if len(preferred) == 1:
            return ResolutionResult(original=val, resolved=preferred[0])

    if len(candidates) > 1:
        return ResolutionResult(
            original=val,
            resolved=candidates[0],
            ambiguous=True,
            ambiguous_candidates=candidates,
        )

    val_norm = val.lower().replace(" ", "")
    norm_matches = [n for n in known_names if n.lower().replace(" ", "") == val_norm]
    if len(norm_matches) == 1:
        return ResolutionResult(original=val, resolved=norm_matches[0])
    if len(norm_matches) > 1:
        return ResolutionResult(
            original=val,
            resolved=norm_matches[0],
            ambiguous=True,
            ambiguous_candidates=norm_matches,
        )

    return ResolutionResult(original=val, resolved=None)


def build_alias_lookup(
    records: list[dict[str, Any]],
    *,
    alt_field: Optional[str] = None,
) -> dict[str, str]:
    """Map lookup aliases (project_name, item_code, …) to canonical ERPNext `name`."""
    alias_to_name: dict[str, str] = {}
    for row in records:
        name = row.get("name")
        if not name:
            continue
        canonical = str(name).strip()
        if not canonical:
            continue
        alias_to_name[canonical] = canonical
        if alt_field:
            alt = row.get(alt_field)
            if alt:
                alias_to_name[str(alt).strip()] = canonical
    return alias_to_name


class BulkLinkResolver:
    """Fetches live ERP master names once per doctype and builds a resolution map."""

    @staticmethod
    async def build_resolution_map(
        adapter: ERPAdapter,
        link_targets: dict[str, set[str]],
        log=None,
        preferred_abbr: Optional[str] = None,
    ) -> ResolutionMap:
        log = log or logger
        result = ResolutionMap()

        for target_doctype, values in link_targets.items():
            if not values:
                continue

            alt_field = _DOCTYPE_ALT_LOOKUP_FIELDS.get(target_doctype)
            list_fields = ["name"]
            if alt_field:
                list_fields.append(alt_field)

            alias_to_name: dict[str, str] = {}
            try:
                if target_doctype in _DOCTYPES_WITHOUT_DISABLED:
                    records = await adapter.list_records(
                        target_doctype, list_fields, limit=2000
                    )
                else:
                    records = await adapter.list_records(
                        target_doctype,
                        list_fields + ["disabled"],
                        filters=[["disabled", "=", 0]],
                    )
                alias_to_name = build_alias_lookup(records, alt_field=alt_field)
            except Exception as e:
                log.warning(
                    "BulkLinkResolver: disabled-filter fetch failed for %s: %s",
                    target_doctype,
                    e,
                )
                try:
                    records = await adapter.list_records(
                        target_doctype, list_fields, limit=2000
                    )
                    alias_to_name = build_alias_lookup(records, alt_field=alt_field)
                except Exception as e2:
                    log.warning(
                        "BulkLinkResolver: fallback fetch failed for %s: %s",
                        target_doctype,
                        e2,
                    )
                    result.unresolvable[target_doctype] = sorted(values)
                    continue

            known_names = list(alias_to_name.keys())

            for val in sorted(values):
                if not val:
                    continue

                candidates = [val]
                if target_doctype == "UOM":
                    alias = _kb_uom_alias(val)
                    if alias and alias not in candidates:
                        candidates.append(alias)

                res = ResolutionResult(original=val, resolved=None)
                for candidate in candidates:
                    attempt = resolve_single(candidate, known_names, preferred_abbr=preferred_abbr)
                    if attempt.resolved:
                        res = ResolutionResult(
                            original=val,
                            resolved=attempt.resolved,
                            ambiguous=attempt.ambiguous,
                            ambiguous_candidates=attempt.ambiguous_candidates,
                        )
                        break
                canonical = (
                    alias_to_name.get(res.resolved, res.resolved)
                    if res.resolved
                    else alias_to_name.get(val)
                )
                if canonical and canonical != val:
                    result.resolved.setdefault(target_doctype, {})[val] = canonical
                    log.info(
                        "BulkLinkResolver: %s '%s' -> '%s'",
                        target_doctype,
                        val,
                        canonical,
                    )
                elif canonical == val or (res.resolved == val and val in alias_to_name):
                    pass
                elif res.ambiguous and res.resolved:
                    picked = alias_to_name.get(res.resolved, res.resolved)
                    result.resolved.setdefault(target_doctype, {})[val] = picked
                    result.ambiguous.setdefault(target_doctype, []).append(
                        (val, res.resolved, res.ambiguous_candidates)
                    )
                    log.warning(
                        "BulkLinkResolver: ambiguous %s '%s' -> picked '%s' from %s",
                        target_doctype,
                        val,
                        res.resolved,
                        res.ambiguous_candidates,
                    )
                else:
                    result.unresolvable.setdefault(target_doctype, []).append(val)
                    log.warning(
                        "BulkLinkResolver: unresolvable %s '%s'",
                        target_doctype,
                        val,
                    )

        return result

    @staticmethod
    def collect_link_targets_from_rows(
        rows: list[dict[str, Any]],
        effective_link_fields: dict[str, str],
    ) -> dict[str, set[str]]:
        """Scan rows (including nested child tables) for link field values."""
        targets: dict[str, set[str]] = {}

        def _scan_obj(obj: Any) -> None:
            if not isinstance(obj, dict):
                return
            for field_name, field_value in obj.items():
                if isinstance(field_value, str) and field_value.strip():
                    target_dt = effective_link_fields.get(field_name)
                    if target_dt:
                        targets.setdefault(target_dt, set()).add(field_value.strip())
                elif isinstance(field_value, list):
                    for item in field_value:
                        if isinstance(item, dict):
                            _scan_obj(item)

        for row in rows:
            _scan_obj(row)

        return targets

    @staticmethod
    def apply_resolution_map_to_rows(
        rows: list[dict[str, Any]],
        effective_link_fields: dict[str, str],
        resolution_map: ResolutionMap,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Rewrite link fields in rows using the resolution map."""
        rewritten = [copy.deepcopy(r) for r in rows]
        corrections: list[dict[str, str]] = []
        unresolvable_hits: list[dict[str, str]] = []

        def _apply_obj(obj: dict) -> None:
            for field_name, field_value in list(obj.items()):
                if isinstance(field_value, str) and field_value.strip():
                    target_dt = effective_link_fields.get(field_name)
                    if not target_dt:
                        continue
                    canonical = resolution_map.resolved.get(target_dt, {}).get(field_value)
                    if canonical and canonical != field_value:
                        obj[field_name] = canonical
                        corrections.append({
                            "field": field_name,
                            "target_doctype": target_dt,
                            "original": field_value,
                            "corrected": canonical,
                        })
                    elif field_value in resolution_map.unresolvable.get(target_dt, []):
                        unresolvable_hits.append({
                            "field": field_name,
                            "target_doctype": target_dt,
                            "value": field_value,
                        })
                elif isinstance(field_value, list):
                    for item in field_value:
                        if isinstance(item, dict):
                            _apply_obj(item)

        for row in rewritten:
            _apply_obj(row)

        summary = {
            "resolved_count": len(corrections),
            "corrections": corrections,
            "unresolvable_values": unresolvable_hits,
            "ambiguous": {
                dt: [
                    {"original": orig, "picked": picked, "candidates": candidates}
                    for orig, picked, candidates in entries
                ]
                for dt, entries in resolution_map.ambiguous.items()
            },
        }
        return rewritten, summary
