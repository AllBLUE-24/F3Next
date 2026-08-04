"""
Apply structured resolutions from supervisor chat user_note to mapped R2 payloads.

Used when the user replies to blocking LER / validation prompts with free-text
instructions (defaults, link targets, party stubs) — project-agnostic.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from containers.implementation.is_common.transactional_party_stubs import (
    inject_party_master_stub,
)

_NORM = lambda s: re.sub(r"\s+", " ", str(s or "").strip().lower())

# "Company: Green Surface Limited" / "1. Company: ..."
_NAMED_RESOLUTION = re.compile(
    r"(?:^\s*\d+\.\s*)?"
    r"(Company|Customer Group|Supplier Group|Warehouse|Supplier|Customer|Item(?: Group)?|Territory|UOM)"
    r"\s*:\s*(.+)$",
    re.I | re.M,
)

# warehouse alias lines: Raw Material Store: "Raw Material Store - GSL"
_WAREHOUSE_ALIAS = re.compile(
    r"^\s*[-•*]?\s*(.+?)\s*:\s*[\"']?([^\"'\n]+)[\"']?\s*$",
    re.M,
)

# file -> doctype: product_master.xlsx -> Item
_FILE_DOCTYPE = re.compile(
    r"([\w.-]+\.(?:xlsx|xls|csv))\s*(?:->|→|—|-)\s*(\w[\w\s]*)",
    re.I,
)

# default vendor is "Aditya Chemicals Ltd"
_DEFAULT_VENDOR = re.compile(
    r"default\s+(?:vendor|supplier)\s+(?:is\s+)?[\"']?([^\"'\n.]+)[\"']?",
    re.I,
)

_FIELD_FOR_TARGET: Dict[str, List[str]] = {
    "Company": ["company"],
    "Customer": ["customer", "customer_name"],
    "Supplier": ["supplier", "supplier_name"],
    "Warehouse": ["warehouse", "warehouse_name", "wip_warehouse", "fg_warehouse", "source_warehouse", "target_warehouse"],
    "Customer Group": ["customer_group"],
    "Supplier Group": ["supplier_group"],
    "Item Group": ["item_group"],
    "Territory": ["territory"],
    "UOM": ["stock_uom", "uom"],
}


def _parse_resolutions_heuristic(user_note: str) -> Dict[str, Any]:
    """Deterministic parse for common free-text supervisor answers."""
    note = (user_note or "").strip()
    out: Dict[str, Any] = {
        "link_defaults": [],
        "party_stubs": [],
        "field_patches": [],
        "warehouse_aliases": {},
        "file_doctype_rules": [],
    }
    if not note:
        return out

    for m in _NAMED_RESOLUTION.finditer(note):
        target = m.group(1).strip()
        value = m.group(2).strip().strip(".")
        if target.lower() == "warehouse" and "map" in value.lower():
            continue
        if target.lower() in ("customer group", "supplier group", "item group", "territory", "uom"):
            out["field_patches"].append({"target_doctype": target, "value": value})
        elif target.lower() in ("company", "supplier", "customer", "item"):
            out["party_stubs"].append({"doctype": target.title() if target.lower() != "item" else "Item", "name": value})
            out["link_defaults"].append({"target_doctype": target.title() if target.lower() != "item" else "Item", "value": value})
        else:
            out["link_defaults"].append({"target_doctype": target, "value": value})

    for m in _WAREHOUSE_ALIAS.finditer(note):
        alias, resolved = m.group(1).strip(), m.group(2).strip()
        if alias and resolved and len(alias) < 80:
            out["warehouse_aliases"][_NORM(alias)] = resolved

    for m in _FILE_DOCTYPE.finditer(note):
        out["file_doctype_rules"].append({"file": m.group(1).strip(), "doctype": m.group(2).strip()})

    dm = _DEFAULT_VENDOR.search(note)
    if dm:
        name = dm.group(1).strip()
        out["party_stubs"].append({"doctype": "Supplier", "name": name})
        out["link_defaults"].append({"target_doctype": "Supplier", "field": "supplier", "value": name, "fill_empty_only": True})

    return out


def _parse_resolutions_llm(user_note: str, sample_gaps: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    try:
        from shared.shared_llm import generate_json

        prompt = f"""Extract ERP import resolutions from the user's supervisor chat reply.

OPEN VALIDATION GAPS (JSON):
{json.dumps(sample_gaps[:8], default=str)[:4000]}

USER REPLY:
{user_note[:6000]}

Return JSON only:
{{
  "link_defaults": [
    {{"target_doctype": "Supplier", "field": "supplier", "value": "Vendor Name", "fill_empty_only": true}}
  ],
  "party_stubs": [{{"doctype": "Supplier", "name": "Vendor Name"}}],
  "field_patches": [{{"target_doctype": "Customer Group", "field": "customer_group", "value": "Commercial"}}],
  "warehouse_aliases": {{"raw material store": "Raw Material Store - GSL"}},
  "file_doctype_rules": [{{"file": "product_master.xlsx", "doctype": "Item"}}]
}}

Rules:
- link_defaults: map link/master values the user specified (use fill_empty_only true when they say "default").
- party_stubs: masters to create (Company, Supplier, Customer, Item).
- field_patches: enum/config fields like customer_group, item_group.
- warehouse_aliases: label -> ERP warehouse name.
- file_doctype_rules: strict file to doctype assignments for re-mapping.
- Only include items explicitly stated by the user."""
        result = generate_json(prompt, temperature=0.0, max_output_tokens=1200)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    return None


async def _list_session_mapped_doctypes(session_id: str) -> List[str]:
    import uuid

    from sqlalchemy import select

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISMappedData

    try:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(ISMappedData.target_doctype).where(
                        ISMappedData.session_id == uuid.UUID(session_id),
                        ISMappedData.total_rows > 0,
                    )
                )
            ).scalars().all()
        return sorted({str(d) for d in rows if d})
    except Exception:
        return []


def parse_user_note_resolutions(
    user_note: str,
    sample_gaps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Merge heuristic + optional LLM extraction."""
    heuristic = _parse_resolutions_heuristic(user_note)
    llm = _parse_resolutions_llm(user_note, sample_gaps or []) if user_note else None
    if not llm:
        return heuristic

    merged = dict(heuristic)
    for key in ("link_defaults", "party_stubs", "field_patches", "file_doctype_rules"):
        llm_items = llm.get(key) if isinstance(llm.get(key), list) else []
        existing = merged.get(key) or []
        seen = {json.dumps(x, sort_keys=True, default=str) for x in existing if isinstance(x, dict)}
        for item in llm_items:
            if isinstance(item, dict) and json.dumps(item, sort_keys=True, default=str) not in seen:
                existing.append(item)
                seen.add(json.dumps(item, sort_keys=True, default=str))
        merged[key] = existing

    wh = dict(heuristic.get("warehouse_aliases") or {})
    if isinstance(llm.get("warehouse_aliases"), dict):
        wh.update({str(k): str(v) for k, v in llm["warehouse_aliases"].items()})
    merged["warehouse_aliases"] = wh
    return merged


def _fields_for_target(target_doctype: str, explicit_field: Optional[str] = None) -> List[str]:
    if explicit_field:
        return [explicit_field]
    return _FIELD_FOR_TARGET.get(target_doctype, [target_doctype.lower().replace(" ", "_")])


def _resolve_warehouse(value: str, aliases: Dict[str, str]) -> str:
    key = _NORM(value)
    return aliases.get(key, value)


def apply_resolutions_to_mapped_data(
    mapped_data: Dict[str, Dict[str, Any]],
    resolutions: Dict[str, Any],
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Patch in-memory mapped payloads; returns (updated, audit)."""
    audit: List[Dict[str, Any]] = []
    out = {dt: dict(payload) for dt, payload in mapped_data.items()}
    aliases = resolutions.get("warehouse_aliases") or {}

    # Party master stubs
    for stub in resolutions.get("party_stubs") or []:
        if not isinstance(stub, dict):
            continue
        dt = str(stub.get("doctype") or "")
        name = str(stub.get("name") or "").strip()
        if not dt or not name:
            continue
        enriched, changed = inject_party_master_stub(out, master_doctype=dt, name=name)
        if changed:
            out = enriched
            audit.append({"op": "party_stub", "doctype": dt, "name": name})

    # Field patches (customer_group, etc.) — apply to all doctypes with that field
    for patch in resolutions.get("field_patches") or []:
        if not isinstance(patch, dict):
            continue
        target = str(patch.get("target_doctype") or patch.get("field") or "")
        value = str(patch.get("value") or "").strip()
        if not target or not value:
            continue
        fields = _fields_for_target(target, patch.get("field"))
        n = 0
        for dt, payload in out.items():
            records = payload.get("records") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                for field in fields:
                    if field in rec and (rec.get(field) in (None, "") or not patch.get("fill_empty_only")):
                        rec[field] = value
                        n += 1
                    elif field in rec or any(f in rec for f in fields):
                        # Set if field exists key-wise in schema expectations
                        if rec.get(field) in (None, ""):
                            rec[field] = value
                            n += 1
        if n:
            audit.append({"op": "field_patch", "target": target, "value": value, "rows": n})

    # Link defaults — fill empty or replace unresolvable values
    for link in resolutions.get("link_defaults") or []:
        if not isinstance(link, dict):
            continue
        target = str(link.get("target_doctype") or "")
        value = str(link.get("value") or "").strip()
        if not value:
            continue
        fields = _fields_for_target(target, link.get("field"))
        fill_empty_only = bool(link.get("fill_empty_only", False))
        n = 0
        for dt, payload in out.items():
            records = payload.get("records") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                for field in fields:
                    if field not in rec:
                        continue
                    cur = rec.get(field)
                    if fill_empty_only and cur not in (None, ""):
                        continue
                    new_val = _resolve_warehouse(value, aliases) if "warehouse" in field else value
                    if cur != new_val:
                        rec[field] = new_val
                        n += 1
        if n:
            audit.append({"op": "link_default", "target": target, "value": value, "rows": n})

    # Warehouse alias replacements on existing values
    if aliases:
        n = 0
        for dt, payload in out.items():
            records = payload.get("records") if isinstance(payload, dict) else None
            if not isinstance(records, list):
                continue
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                for field in _FIELD_FOR_TARGET.get("Warehouse", []):
                    if field not in rec:
                        continue
                    cur = rec.get(field)
                    if isinstance(cur, str) and _NORM(cur) in aliases:
                        rec[field] = aliases[_NORM(cur)]
                        n += 1
        if n:
            audit.append({"op": "warehouse_alias", "rows": n})

    return out, audit


async def apply_user_note_resolutions(
    *,
    session_id: str,
    project_id: str,
    company_slug: str,
    user_note: str,
    sample_gaps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Load R2 payloads, apply parsed resolutions, persist, return audit."""
    from shared.r2_client import r2_read_json, r2_write_json

    resolutions = parse_user_note_resolutions(user_note, sample_gaps)
    mapped_data: Dict[str, Dict[str, Any]] = {}

    for dt in await _list_session_mapped_doctypes(session_id):
        key = f"{company_slug}/{project_id}/mappings/mapped_payloads/{dt}.json"
        try:
            payload = await r2_read_json(key, bucket="clean-data") or {}
            if isinstance(payload, dict):
                mapped_data[dt] = payload
        except Exception:
            continue

    if not mapped_data:
        return {"status": "no_payloads", "resolutions": resolutions}

    updated, audit = apply_resolutions_to_mapped_data(mapped_data, resolutions)
    written = 0
    for dt, payload in updated.items():
        before = mapped_data.get(dt, {})
        if payload.get("records") == before.get("records"):
            continue
        key = f"{company_slug}/{project_id}/mappings/mapped_payloads/{dt}.json"
        await r2_write_json(key, payload, bucket="clean-data")
        written += 1

    # Persist file→doctype rules for future mapping passes
    rules = resolutions.get("file_doctype_rules") or []
    if rules and user_note:
        try:
            import uuid
            from datetime import datetime

            from sqlalchemy import select, update

            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISSession

            async with AsyncSessionLocal() as session:
                row = (
                    await session.execute(select(ISSession).where(ISSession.id == uuid.UUID(session_id)))
                ).scalar_one_or_none()
                if row:
                    notes = list(row.user_notes or [])
                    notes.append({
                        "type": "mapping_rules",
                        "source": "supervisor_user_note",
                        "note": user_note[:8000],
                        "file_doctype_rules": rules,
                        "answered_at": datetime.utcnow().isoformat() + "Z",
                    })
                    await session.execute(
                        update(ISSession)
                        .where(ISSession.id == row.id)
                        .values(
                            user_import_note=user_note[:8000],
                            user_notes=notes,
                        )
                    )
                    await session.commit()
        except Exception:
            pass

    return {
        "status": "ok",
        "written": written,
        "audit": audit,
        "resolutions": resolutions,
    }
