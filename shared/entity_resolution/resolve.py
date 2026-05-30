"""
Batch entity resolution against a live link_cache.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from shared.erp_adapters.link_resolver import ResolutionMap, resolve_single
@dataclass
class ResolvedEntities:
    """Canonical ERP-oriented entities after LER."""

    customer: Optional[str] = None
    supplier: Optional[str] = None
    company: Optional[str] = None
    items: list[dict[str, Any]] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)
    ambiguous: dict[str, list[str]] = field(default_factory=dict)
    unresolved: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = dict(self.extras)
        if self.customer:
            out["customer"] = self.customer
        if self.supplier:
            out["supplier"] = self.supplier
        if self.company:
            out["company"] = self.company
        if self.items:
            out["items"] = self.items
        if self.ambiguous:
            out["_ler_ambiguous"] = self.ambiguous
        if self.unresolved:
            out["_ler_unresolved"] = self.unresolved
        return out


def _resolve_value(
    raw: str,
    known_names: list[str],
    *,
    preferred_abbr: Optional[str] = None,
) -> tuple[Optional[str], bool, list[str]]:
    res = resolve_single(raw.strip(), known_names, preferred_abbr=preferred_abbr)
    if res.resolved:
        return res.resolved, res.ambiguous, list(res.ambiguous_candidates)
    return None, False, []


def resolve_entities_batch(
    raw_entities: dict[str, Any],
    link_cache: dict[str, list[str]],
    *,
    doctype: str = "",
    preferred_abbr: Optional[str] = None,
) -> ResolvedEntities:
    """
    Resolve party / item / company strings against *link_cache* (live ERP lists).
    """
    result = ResolvedEntities()
    ent = raw_entities if isinstance(raw_entities, dict) else {}

    for key in ("customer", "supplier", "company"):
        raw = ent.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        target_dt = "Customer" if key == "customer" else "Supplier" if key == "supplier" else "Company"
        known = link_cache.get(target_dt) or []
        canonical, amb, cands = _resolve_value(raw, known, preferred_abbr=preferred_abbr)
        if canonical:
            setattr(result, key, canonical)
            if amb:
                result.ambiguous.setdefault(key, cands)
        else:
            result.unresolved.setdefault(key, []).append(raw.strip())

    items_raw = ent.get("items")
    if isinstance(items_raw, list):
        known_items = link_cache.get("Item") or []
        resolved_items: list[dict[str, Any]] = []
        for row in items_raw:
            if not isinstance(row, dict):
                continue
            new_row = dict(row)
            code = str(row.get("item_code") or row.get("item_name") or "").strip()
            if code:
                canonical, amb, cands = _resolve_value(
                    code, known_items, preferred_abbr=preferred_abbr,
                )
                if canonical:
                    new_row["item_code"] = canonical
                    if amb:
                        result.ambiguous.setdefault("item_code", cands)
                else:
                    result.unresolved.setdefault("item_code", []).append(code)
            resolved_items.append(new_row)
        result.items = resolved_items

    reserved = {"customer", "supplier", "company", "items", "_cvs_miss_customer", "_cvs_miss_item"}
    for k, v in ent.items():
        if k not in reserved:
            result.extras[k] = v

    _ = doctype
    return result


async def resolve_links_for_command(
    adapter,
    intent: dict[str, Any],
    *,
    preferred_abbr: Optional[str] = None,
    log=None,
) -> tuple[dict[str, list[str]], ResolutionMap, ResolvedEntities]:
    """
    End-to-end LER for one OS command intent (no Temporal).

    Returns ``(link_cache, resolution_map, resolved_entities)``.
    """
    from shared.entity_resolution.ler import build_link_cache, build_resolution_map
    from shared.entity_resolution.targets import collect_link_targets_from_intent

    doctype = str(intent.get("target_doctype") or "").strip()
    targets = collect_link_targets_from_intent(intent, doctype)
    link_cache = await build_link_cache(adapter, targets, preferred_abbr=preferred_abbr, log=log)
    resolution_map = await build_resolution_map(
        adapter, targets, preferred_abbr=preferred_abbr, log=log,
    )

    entities = intent.get("entities") if isinstance(intent.get("entities"), dict) else {}
    resolved = resolve_entities_batch(
        entities,
        link_cache,
        doctype=doctype,
        preferred_abbr=preferred_abbr,
    )

    for target_dt, mapping in resolution_map.resolved.items():
        for _orig, canonical in mapping.items():
            if target_dt == "Customer" and not resolved.customer:
                resolved.customer = canonical
            elif target_dt == "Supplier" and not resolved.supplier:
                resolved.supplier = canonical
            elif target_dt == "Company" and not resolved.company:
                resolved.company = canonical

    return link_cache, resolution_map, resolved
