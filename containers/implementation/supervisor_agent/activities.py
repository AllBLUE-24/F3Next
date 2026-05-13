"""
Supervisor Agent — Temporal activities for supervised correction loops.

v0 skeleton:
- Retrieves explanatory context from pgvector collections (via rag_helper),
  but makes no decisions and applies no patches yet.
- Returns SupervisorResult with empty actions by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from temporalio import activity

from shared.models.is_status import (
    ApplyActionsResult,
    ApplySupervisorActionsInput,
    NodeStatusEnvelope,
    SupervisorAction,
    SupervisorResult,
)


@dataclass
class SuperviseStepInput:
    project_id: str
    session_id: str
    node_name: str
    step: str
    f3iche_id: str = ""
    phase: Optional[str] = None
    doctypes_in_focus: List[str] = field(default_factory=list)
    status: Optional[NodeStatusEnvelope] = None


@activity.defn(name="supervise_step")
async def supervise_step(inp: SuperviseStepInput) -> SupervisorResult:
    """
    Inspect a node's NodeStatusEnvelope and retrieve relevant KB chunks for
    explanation. Decision-making is intentionally no-op in this skeleton.
    """

    st = inp.status or NodeStatusEnvelope.partial(primary_result=None)
    activity.logger.info(
        "▶ supervise_step started | node=%s step=%s status=%s errors=%d warnings=%d",
        inp.node_name,
        inp.step,
        st.status,
        len(st.errors),
        len(st.warnings),
    )

    # Retrieve context (best-effort). This is used for future explanation/prompting.
    rag: Dict[str, List[str]] = {}
    query_text = f"{inp.node_name} {inp.f3iche_id} {' '.join(inp.doctypes_in_focus)}"

    try:
        from containers.implementation.utils.rag_helper import rag_retrieve

        # pgvector_kb_design.md expects these kb_source prefixes.
        if inp.project_id:
            rag["company"] = await rag_retrieve(query_text, f"company_{inp.project_id}", top_k=3)
        if inp.f3iche_id:
            rag["f3iche"] = await rag_retrieve(query_text, f"f3iche_{inp.f3iche_id}", top_k=5)
            rag["industry_reality"] = await rag_retrieve(
                query_text,
                f"industry_reality_{inp.f3iche_id}",
                top_k=4,
            )
        rag["erpnext_docs"] = await rag_retrieve(query_text, "erpnext_docs", top_k=5)
    except Exception as e:
        activity.logger.warning("  ⚠️ Supervisor RAG retrieval failed (non-fatal): %s", e)

    actions: List[SupervisorAction] = []
    final_status: str = "resolved"

    # v1 logic: handle validation plus readiness in a deterministic, rules-based way.
    if inp.node_name == "validate_mapped_data":
        missing_required: List[str] = []
        enum_status_bad = False
        units_in_numeric = False

        # Parse error/warning messages emitted by Validation Agent.
        for e in (st.errors or []):
            msg = str(e.get("message", ""))
            if "Missing required field:" in msg:
                missing_required.append(msg.split("Missing required field:", 1)[1].strip())

        for w in (st.warnings or []):
            msg = str(w.get("message", ""))
            if "invalid enum value for 'status'" in msg and ("PASS" in msg or "FAIL" in msg):
                enum_status_bad = True
            if "Non-numeric value" in msg and ("qty" in msg or "amount" in msg or "rate" in msg):
                units_in_numeric = True

        # Safe auto-fixes (patch R2 mapped payloads).
        if enum_status_bad:
            actions.append(
                SupervisorAction(
                    id="auto_fix_work_order_status_pass_fail",
                    type="auto_fix",
                    scope="Work Order",
                    changes=[
                        {
                            "target": "r2",
                            "doctype": "Work Order",
                            "op": "map_enum",
                            "field": "status",
                            "map": {"PASS": "Completed", "FAIL": "Stopped"},
                        }
                    ],
                    metadata={"reason": "ERPNext Work Order status enum mismatch"},
                )
            )

        if units_in_numeric:
            actions.append(
                SupervisorAction(
                    id="auto_fix_strip_units_numeric_fields",
                    type="auto_fix",
                    scope="records",
                    changes=[
                        {
                            "target": "r2",
                            "doctype": "Work Order",
                            "op": "strip_units",
                            "fields": ["qty", "produced_qty"],
                        }
                    ],
                    metadata={"reason": "Numeric fields contain units (e.g. '500 Gal')"},
                )
            )

        # Blocking gaps → ask user (Supervisor prompt)
        if missing_required:
            final_status = "needs_user_input"
            actions.append(
                SupervisorAction(
                    id="ask_user_missing_required_fields",
                    type="ask_user",
                    scope="validation",
                    question=(
                        "Some required fields are missing for import. "
                        f"Missing: {', '.join(sorted(set(missing_required)))}. "
                        "How should we resolve these?"
                    ),
                    options=[
                        "Provide defaults where possible (warehouses/company), and re-run validation",
                        "I will upload the missing prerequisite data (e.g., BOMs) and re-run validation",
                        "Proceed anyway (not recommended)",
                    ],
                    metadata={"missing_required_fields": sorted(set(missing_required))},
                )
            )

    elif inp.node_name == "assess_data_readiness":
        assessment = (st.primary_result or {}).get("assessment", {}) if isinstance(st.primary_result, dict) else {}

        missing_doctypes = assessment.get("missing_doctypes", []) or []
        partial_doctypes = assessment.get("partial_doctypes", []) or []
        unmappable_chunks = assessment.get("unmappable_chunks", []) or []

        critical_missing = [
            g for g in missing_doctypes
            if str(g.get("criticality", "")).lower() == "critical"
        ]
        noncritical_missing = [
            g for g in missing_doctypes
            if str(g.get("criticality", "")).lower() in ("non_critical", "optional")
            or bool(g.get("can_proceed_without", False))
        ]
        critical_partial = [
            g for g in partial_doctypes
            if str(g.get("criticality", "")).lower() == "critical"
        ]

        if critical_missing or critical_partial or noncritical_missing:
            missing_names = sorted({
                g.get("doctype", "")
                for g in (*critical_missing, *critical_partial, *noncritical_missing)
                if g.get("doctype", "")
            })
            q_prefix = "Critical" if (critical_missing or critical_partial) else "Non-critical"
            question = (
                f"{q_prefix} data is missing for: {', '.join([n for n in missing_names if n])}. "
                "How would you like to proceed?"
            )

            options = [
                "Upload Missing Files",
                "Proceed with Partial Data",
                "Skip These Doctypes",
            ]
            if unmappable_chunks:
                question += f" {len(unmappable_chunks)} uploaded file section(s) could not be matched to ERPNext doctypes."

            if critical_missing or critical_partial:
                final_status = "needs_user_input"

            actions.append(
                SupervisorAction(
                    id="ask_user_data_readiness",
                    type="ask_user",
                    scope="data_readiness",
                    question=question,
                    options=options,
                    metadata={
                        "critical_missing": critical_missing,
                        "critical_partial": critical_partial,
                        "noncritical_missing": noncritical_missing,
                        "unmappable_chunks": unmappable_chunks,
                    },
                )
            )

    retrieved_blocks = ", ".join(sorted([k for k, v in rag.items() if v])) or "none"
    summary = (
        f"{inp.node_name}: status={st.status}, errors={len(st.errors)}, warnings={len(st.warnings)}. "
        f"Retrieved context blocks: {retrieved_blocks}."
    )

    activity.logger.info("✅ supervise_step done | final_status=%s actions=%d", final_status, len(actions))
    return SupervisorResult(actions=actions, summary_for_ui=summary, final_status=final_status)  # type: ignore[arg-type]


@activity.defn(name="apply_supervisor_actions")
async def apply_supervisor_actions(inp: ApplySupervisorActionsInput) -> ApplyActionsResult:
    """
    v0 skeleton: does not apply any patches yet.
    """

    activity.logger.info(
        "▶ apply_supervisor_actions started | project=%s step=%s actions=%d",
        inp.project_id,
        inp.step,
        len(inp.actions or []),
    )

    applied: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    company_slug = inp.company_slug or "unknown"

    # Best-effort patching of R2 mapped payloads for supported transforms.
    for act in inp.actions or []:
        if act.type != "auto_fix":
            skipped.append({"id": act.id, "type": act.type, "scope": act.scope, "reason": "not_auto_fix"})
            continue

        for ch in act.changes or []:
            if ch.get("target") != "r2":
                skipped.append({"id": act.id, "change": ch, "reason": "unsupported_target"})
                continue

            doctype = ch.get("doctype")
            if not doctype:
                skipped.append({"id": act.id, "change": ch, "reason": "missing_doctype"})
                continue

            key = f"{company_slug}/{inp.project_id}/mappings/mapped_payloads/{doctype}.json"
            try:
                from shared.r2_client import r2_read_json, r2_write_json

                payload = await r2_read_json(key, bucket="clean-data") or {}
                records = payload.get("records") if isinstance(payload, dict) else None
                if not isinstance(records, list):
                    skipped.append({"id": act.id, "doctype": doctype, "reason": "no_records_array"})
                    continue

                op = ch.get("op")
                if op == "map_enum":
                    field_name = ch.get("field")
                    mapping = ch.get("map") or {}
                    if not field_name or not isinstance(mapping, dict):
                        skipped.append({"id": act.id, "doctype": doctype, "reason": "bad_map_enum_change"})
                        continue
                    n = 0
                    for r in records:
                        if isinstance(r, dict) and r.get(field_name) in mapping:
                            r[field_name] = mapping[r[field_name]]
                            n += 1
                    await r2_write_json(key, payload, bucket="clean-data")
                    applied.append({"id": act.id, "doctype": doctype, "op": op, "updated": n, "key": key})
                    continue

                if op == "strip_units":
                    fields = ch.get("fields") or []
                    if not isinstance(fields, list) or not fields:
                        skipped.append({"id": act.id, "doctype": doctype, "reason": "bad_strip_units_change"})
                        continue
                    import re

                    num_re = re.compile(r"-?\d+(?:\.\d+)?")
                    n = 0
                    for r in records:
                        if not isinstance(r, dict):
                            continue
                        for fn in fields:
                            v = r.get(fn)
                            if isinstance(v, str):
                                m = num_re.search(v.replace(",", ""))
                                if m:
                                    num_s = m.group(0)
                                    r[fn] = float(num_s) if "." in num_s else int(num_s)
                                    n += 1
                    await r2_write_json(key, payload, bucket="clean-data")
                    applied.append({"id": act.id, "doctype": doctype, "op": op, "updated": n, "key": key})
                    continue

                skipped.append({"id": act.id, "doctype": doctype, "reason": f"unsupported_op:{op}"})
            except Exception as e:
                errors.append({"id": act.id, "doctype": doctype, "error": str(e), "key": key})

    activity.logger.info(
        "✅ apply_supervisor_actions done | applied=%d skipped=%d errors=%d",
        len(applied),
        len(skipped),
        len(errors),
    )
    return ApplyActionsResult(applied=applied, skipped=skipped, errors=errors)

