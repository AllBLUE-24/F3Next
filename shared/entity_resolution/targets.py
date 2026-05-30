"""
Collect link resolution targets from OS intent / entities (KB-driven).
"""

from __future__ import annotations

from typing import Any

from shared.erp_semantics import (
    get_field_mappings,
    is_link_field_spec,
    link_target_doctype,
    normalize_items_list,
    resolve_entity_to_field,
)


def collect_link_targets_from_intent(
    intent: dict[str, Any],
    doctype: str,
    *,
    kb_schema: dict[str, Any] | None = None,
) -> dict[str, set[str]]:
    """
    Scan intent entities for Link field values that need LER resolution.

    Returns ``{erp_doctype: {raw values}}`` suitable for ``build_resolution_map``.
    """
    _ = kb_schema  # reserved for branch-02 context engine overlay
    targets: dict[str, set[str]] = {}
    entities = intent.get("entities") if isinstance(intent.get("entities"), dict) else {}
    if not entities:
        return targets

    dt = str(doctype or intent.get("target_doctype") or "").strip()
    if not dt:
        return targets

    def _add(target_dt: str, value: str) -> None:
        v = value.strip()
        if v and target_dt:
            targets.setdefault(target_dt, set()).add(v)

    for entity_key, raw_value in entities.items():
        if entity_key == "items":
            for row in normalize_items_list(raw_value):
                code = str(row.get("item_code") or row.get("item_name") or "").strip()
                if code:
                    _add("Item", code)
            continue
        if not isinstance(raw_value, str) or not raw_value.strip():
            continue

        resolved = resolve_entity_to_field(dt, entity_key)
        if resolved:
            _, spec = resolved
            if is_link_field_spec(spec):
                link_dt = link_target_doctype(spec)
                if link_dt:
                    _add(link_dt, raw_value)
                    continue

        fm = get_field_mappings(dt)
        spec = fm.get(entity_key) if isinstance(fm.get(entity_key), dict) else None
        if spec and is_link_field_spec(spec):
            link_dt = link_target_doctype(spec)
            if link_dt:
                _add(link_dt, raw_value)

    company = entities.get("company")
    if isinstance(company, str) and company.strip():
        _add("Company", company)

    profile_company = (intent.get("company_context") or {}).get("company")
    if isinstance(profile_company, str) and profile_company.strip():
        _add("Company", profile_company)

    return targets


def link_field_index_from_intent(intent: dict[str, Any], doctype: str) -> dict[str, str]:
    """Map entity keys → ERP link doctype for ``apply_resolved_to_intent``."""
    index: dict[str, str] = {}
    entities = intent.get("entities") if isinstance(intent.get("entities"), dict) else {}
    dt = str(doctype or intent.get("target_doctype") or "").strip()

    for entity_key in entities:
        if entity_key == "items":
            index["items"] = "Item"
            continue
        resolved = resolve_entity_to_field(dt, entity_key)
        if resolved:
            _, spec = resolved
            if is_link_field_spec(spec):
                link_dt = link_target_doctype(spec)
                if link_dt:
                    index[entity_key] = link_dt
    return index
