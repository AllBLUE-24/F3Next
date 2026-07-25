"""Live-Frappe-first required-field resolution for Step 3."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from containers.implementation.is_common.f3iche_policy import (
    default_when_missing,
    defer_until_post_mvp,
    import_field_policy,
    is_deferred_doctype,
)
from containers.implementation.is_common.required_fields import get_required_fields
from containers.implementation.readiness.config import live_schema_primary


def _mandatory_from_live_fields(live_fields: List[Dict[str, Any]]) -> List[str]:
    names: List[str] = []
    seen: Set[str] = set()
    for field in live_fields or []:
        if not isinstance(field, dict):
            continue
        if not field.get("mandatory"):
            continue
        fname = str(field.get("fieldname") or "").strip()
        if fname and fname not in seen:
            seen.add(fname)
            names.append(fname)
    return names


def _defaults_for_doctype(doctype: str, f3iche_id: Optional[str]) -> Set[str]:
    out: Set[str] = set()
    if not f3iche_id:
        return out
    raw = default_when_missing(f3iche_id)
    prefix = f"{doctype}."
    for key in raw:
        k = str(key or "").strip()
        if not k:
            continue
        if k.startswith(prefix):
            out.add(k[len(prefix):])
        elif "." not in k:
            out.add(k)
    return out


def _always_ask_fields(f3iche_id: Optional[str]) -> Set[str]:
    if not f3iche_id:
        return set()
    policy = import_field_policy(f3iche_id)
    items = policy.get("always_ask") or []
    return {str(x).strip() for x in items if str(x).strip() and "." not in str(x)}


def _deferred_fields(f3iche_id: Optional[str]) -> Set[str]:
    if not f3iche_id:
        return set()
    return defer_until_post_mvp(f3iche_id)


def resolve_required_fields(
    doctype: str,
    *,
    project_id: Optional[str] = None,
    f3iche_id: Optional[str] = None,
    live_fields: Optional[List[Dict[str, Any]]] = None,
) -> tuple[List[str], str]:
    """
    Resolve import-required fieldnames for one doctype.

    Returns (fieldnames, source) where source is ``live``, ``bridge``, or ``deferred``.
    """
    if f3iche_id and is_deferred_doctype(doctype, f3iche_id):
        return [], "deferred"

    source = "bridge"
    if live_fields:
        base = _mandatory_from_live_fields(live_fields)
        source = "live"
    else:
        base = list(get_required_fields(doctype))

    deferred = _deferred_fields(f3iche_id)
    defaults = _defaults_for_doctype(doctype, f3iche_id)
    always_ask = _always_ask_fields(f3iche_id)

    required: List[str] = []
    seen: Set[str] = set()
    for field in list(base) + sorted(always_ask):
        if field in deferred or field in defaults:
            continue
        if field not in seen:
            seen.add(field)
            required.append(field)

    # ``project_id`` is accepted for API symmetry; live fetch happens in async helper.
    _ = project_id
    return required, source


async def resolve_required_fields_async(
    doctype: str,
    *,
    project_id: Optional[str] = None,
    f3iche_id: Optional[str] = None,
) -> tuple[List[str], str]:
    """Fetch live schema when enabled, then delegate to ``resolve_required_fields``."""
    live_fields: Optional[List[Dict[str, Any]]] = None
    if live_schema_primary() and project_id:
        from containers.implementation.mapping_agent.live_schema import fetch_live_doctype_schema

        fetched = await fetch_live_doctype_schema(doctype, project_id)
        if fetched:
            live_fields = fetched
    return resolve_required_fields(
        doctype,
        project_id=project_id,
        f3iche_id=f3iche_id,
        live_fields=live_fields,
    )
