"""Read-only import preflight checks for IS (no ERPNext writes)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from shared.erp_policies.action_risk import build_confirmation_preview, classify_action_risk
from shared.erp_policies.lifecycle import children_requiring_submitted, get_lifecycle_config

logger = logging.getLogger(__name__)


async def scan_draft_parents(
    adapter,
    phase_steps: List[Dict[str, Any]],
    log=None,
) -> List[Dict[str, Any]]:
    """Find draft submittable parents that block downstream create steps."""
    log = log or logger
    drafts: List[Dict[str, Any]] = []

    child_doctypes = {s.get("doctype") for s in phase_steps if s.get("action") == "create"}

    for parent_dt, cfg in _parent_doctypes_for_phase(child_doctypes):
        if not cfg.get("is_submittable"):
            continue
        blocked_children = [
            c for c in cfg.get("children_requiring_submitted", [])
            if c in child_doctypes
        ]
        if not blocked_children:
            continue
        try:
            records = await adapter.list_records(
                parent_dt,
                ["name", "docstatus", "item"],
                filters=[["docstatus", "=", 0]],
                limit=50,
            )
            for rec in records:
                drafts.append({
                    "doctype": parent_dt,
                    "name": rec.get("name"),
                    "docstatus": rec.get("docstatus", 0),
                    "blocks": blocked_children,
                })
        except Exception as exc:
            log.warning("Preflight: could not scan draft %s: %s", parent_dt, exc)

    return drafts


def _parent_doctypes_for_phase(child_doctypes: set) -> List[Tuple[str, dict]]:
    """Return parent doctypes whose submitted state matters for this phase."""
    candidates = ["BOM", "Sales Order", "Purchase Order", "Price List"]
    result: List[Tuple[str, dict]] = []
    for dt in candidates:
        cfg = get_lifecycle_config(dt)
        blocks = cfg.get("children_requiring_submitted") or children_requiring_submitted(dt)
        if any(c in child_doctypes for c in blocks):
            cfg = dict(cfg)
            cfg["children_requiring_submitted"] = blocks
            result.append((dt, cfg))
    return result


async def run_import_preflight(
    *,
    phase_id: str,
    steps: List[Dict[str, Any]],
    s3,
    adapter,
    known_link_fields: Dict[str, str],
    dry_run_link_resolution: bool = True,
    log=None,
) -> Dict[str, Any]:
    """
    Build a read-only preflight report for an import phase.

    When dry_run_link_resolution is True, runs Pass 2.5 logic without POST.
    """
    log = log or logger
    from shared.entity_resolution.rows import (
        apply_resolution_map_to_rows,
        collect_link_targets_from_rows,
    )
    from shared.entity_resolution.ler import build_resolution_map

    data_gaps = [
        {"doctype": s.get("doctype"), "step": s.get("step")}
        for s in steps
        if s.get("action") == "data_gap"
    ]
    create_steps = [s for s in steps if s.get("action") == "create"]

    all_corrections: List[dict] = []
    unresolvable: List[dict] = []

    if dry_run_link_resolution and adapter and create_steps:
        all_link_targets: Dict[str, set] = {}
        for step in create_steps:
            r2_key = step.get("data_source")
            if not r2_key or r2_key in ("none", "pending_mapping"):
                continue
            try:
                resp = s3.get_object(Bucket="clean-data", Key=r2_key)
                payload = json.loads(resp["Body"].read().decode("utf-8"))
                rows = payload.get("records", [])
            except Exception as exc:
                log.warning("Preflight: could not read %s: %s", r2_key, exc)
                continue
            payload_link_fields: Dict[str, str] = payload.get("link_fields", {})
            effective = {**known_link_fields, **payload_link_fields}
            targets = collect_link_targets_from_rows(rows, effective)
            for target_dt, vals in targets.items():
                all_link_targets.setdefault(target_dt, set()).update(vals)

        if all_link_targets:
            resolution_map = await build_resolution_map(
                adapter, all_link_targets, log=log,
            )
            for step in create_steps:
                r2_key = step.get("data_source")
                if not r2_key:
                    continue
                try:
                    resp = s3.get_object(Bucket="clean-data", Key=r2_key)
                    payload = json.loads(resp["Body"].read().decode("utf-8"))
                    rows = payload.get("records", [])
                    effective = {**known_link_fields, **payload.get("link_fields", {})}
                    _, summary = apply_resolution_map_to_rows(
                        rows, effective, resolution_map,
                    )
                    all_corrections.extend(summary.get("corrections", []))
                    unresolvable.extend(summary.get("unresolvable_values", []))
                except Exception:
                    pass

    draft_parents: List[dict] = []
    if adapter and create_steps:
        draft_parents = await scan_draft_parents(adapter, steps, log)

    financial_warnings = [
        f"{s.get('doctype')} ({s.get('records', 0)} records) — financial/high-risk import"
        for s in create_steps
        if classify_action_risk(str(s.get("doctype", "")), "create") == "high"
    ]

    preview = build_confirmation_preview(
        phase_id=phase_id,
        steps=steps,
        draft_parents=draft_parents,
        link_corrections=all_corrections,
        financial_warnings=financial_warnings,
    )

    blockers: List[str] = []
    if unresolvable:
        blockers.append(f"{len(unresolvable)} unresolvable link value(s)")
    if data_gaps:
        blockers.append(f"{len(data_gaps)} data gap(s) in plan")

    return {
        "phase_id": phase_id,
        "status": "blocked" if blockers and not create_steps else "ready",
        "blockers": blockers,
        "data_gaps": data_gaps,
        "link_corrections": all_corrections,
        "unresolvable_links": unresolvable,
        "draft_parents": draft_parents,
        "confirmation_preview": preview,
        "requires_confirmation": preview.get("requires_confirmation", False),
        "requires_execution_gate": (
            phase_id == "phase_c_transactional"
            or preview.get("requires_confirmation", False)
            or bool(draft_parents)
            or bool(financial_warnings)
        ),
    }
