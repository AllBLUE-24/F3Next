"""
Supervisor Agent — Temporal activities for supervised correction loops.

v2 — LLM-driven natural language supervisor messages.

Key changes from v1:
- assess_data_readiness node: calls an LLM (with RAG context) to generate a single,
  clear natural-language message per gap tier rather than generic MCQ options.
- Two tiers:
    CRITICAL  — relational dependency; import literally cannot proceed without it.
    IMPORTANT — industry best-practice gap; can proceed but shouldn't (bad idea).
- Removed: "Skip These Doctypes", "Proceed with Partial Data" options (harmful UX).
- Actions are: "Upload Missing Files" (critical) OR "Continue Anyway" with a
  clear consequence warning (important gaps only).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from temporalio import activity

from pydantic import BaseModel, Field

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


class SupervisorGapMessages(BaseModel):
    """Structured LLM output for supervisor gap copy."""

    critical_message: str = ""
    important_message: str = ""
    critical_doctypes: List[str] = Field(default_factory=list)
    important_doctypes: List[str] = Field(default_factory=list)


# ── LLM prompt for natural-language supervisor messages ────────────────────────

_SUPERVISOR_MESSAGE_PROMPT = """\
You are the Implementation Supervisor for an ERP onboarding system.
A company is importing their data into ERPNext. The data readiness scan has found gaps.
Your job is to write clear, friendly, specific messages to guide the user.

COMPANY CONTEXT:
{company_context}

INDUSTRY KNOWLEDGE:
{industry_context}

GAP ANALYSIS:
{gap_analysis}

INSTRUCTIONS:
Write two messages (only include a tier if it has gaps):

1. CRITICAL_MESSAGE (for critical gaps — relational dependencies ERPNext cannot function without):
   - Be direct but not alarming. Example: "You've uploaded Work Orders but we couldn't find
     any Bills of Materials (BOMs). In ERPNext, every Work Order requires a linked BOM — without
     it, the system literally cannot create the work order. Please upload your BOM data before we continue."
   - Explain WHY it's relational (the ERPNext dependency reason).
   - List each missing item specifically by name.
   - DO NOT say "skip" or suggest ignoring this.

2. IMPORTANT_MESSAGE (for non-critical gaps — industry best practices the company should set up):
   - Frame as a recommendation. Example: "For a chemical manufacturing company like yours,
     you'd typically also want to set up your Quality Control Inspection templates and
     Batch/Lot tracking before going live. These aren't blockers today, but skipping them
     means you'll need to retroactively configure them once you're live — which is painful."
   - Reference their specific industry/business type where relevant.
   - You CAN mention they can continue without these (but should strongly recommend against it).

RULES:
- Be specific — name actual doctypes and explain each one's purpose in plain English.
- Do NOT use jargon without explanation.
- Do NOT suggest skipping critical items.
- Keep each message under 4 sentences.
- If there are no critical gaps, return empty string for CRITICAL_MESSAGE.
- If there are no important gaps, return empty string for IMPORTANT_MESSAGE.

Return ONLY valid JSON:
{{
  "critical_message": "<message or empty string>",
  "important_message": "<message or empty string>",
  "critical_doctypes": ["<list of critical missing doctype names>"],
  "important_doctypes": ["<list of important missing doctype names>"]
}}
"""


async def _call_supervisor_llm(
    gap_analysis: Dict[str, Any],
    rag: Dict[str, List[str]],
    f3iche_id: str,
) -> Dict[str, Any]:
    """Call an LLM to generate rich natural-language supervisor messages."""
    company_ctx = "\n".join(rag.get("company", [])) or "No company context available."
    industry_ctx = "\n".join(
        rag.get("f3iche", []) + rag.get("industry_reality", [])
    ) or "No industry context available."

    prompt = _SUPERVISOR_MESSAGE_PROMPT.format(
        company_context=company_ctx[:1500],
        industry_context=industry_ctx[:1500],
        gap_analysis=json.dumps(gap_analysis, indent=2)[:2000],
    )

    try:
        from shared.structured_llm import generate_typed

        result = await generate_typed(
            prompt=prompt,
            schema=SupervisorGapMessages,
            model_name=os.getenv("SUPERVISOR_MODEL", os.getenv("MAPPING_EXTRACTION_MODEL", "gpt-4o-mini")),
            temperature=0.2,
            max_output_tokens=800,
            system_instruction=(
                "You are an ERP implementation supervisor. Return ONLY valid JSON. "
                "No markdown fences. No explanation text outside the JSON object."
            ),
        )
        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            return json.loads(result)
    except Exception as e:
        activity.logger.warning("  ⚠️ Supervisor LLM call failed: %s", e)

    return {
        "critical_message": "",
        "important_message": "",
        "critical_doctypes": [],
        "important_doctypes": [],
    }


@activity.defn(name="supervise_step")
async def supervise_step(inp: SuperviseStepInput) -> SupervisorResult:
    """
    Inspect a node's NodeStatusEnvelope, retrieve relevant KB chunks via RAG,
    then use an LLM to generate clear natural-language supervisor messages.

    Two-tier gap classification:
      CRITICAL  — ERPNext relational dependency; pipeline cannot continue without it.
      IMPORTANT — Industry best-practice gap; can continue but strongly inadvisable.
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

    # ── RAG retrieval (best-effort) ─────────────────────────────────────────
    rag: Dict[str, List[str]] = {}
    query_text = f"{inp.node_name} {inp.f3iche_id} {' '.join(inp.doctypes_in_focus)}"

    try:
        from containers.implementation.utils.rag_helper import rag_retrieve

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

    # ══════════════════════════════════════════════════════════════════════════
    # NODE: validate_mapped_data
    # ══════════════════════════════════════════════════════════════════════════
    if inp.node_name == "validate_mapped_data":
        missing_required: List[str] = []
        enum_status_bad = False
        units_in_numeric = False

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

        # Auto-fixes (safe, no user needed)
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

        # KB-injectable fields (naming_series, etc.) — auto-fix before asking user
        kb_auto_fields = {"naming_series"}
        checks = (st.primary_result or {}).get("checks") if isinstance(st.primary_result, dict) else []
        if not isinstance(checks, list):
            checks = []

        doctypes_for_kb_fix: List[str] = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            dt = check.get("doctype")
            errs = check.get("errors") or []
            needs_kb = any(
                any(f"Missing required field: {field}" in str(e) for e in errs)
                for field in kb_auto_fields
            )
            if dt and needs_kb and dt not in doctypes_for_kb_fix:
                doctypes_for_kb_fix.append(str(dt))

        for dt in doctypes_for_kb_fix:
            actions.append(
                SupervisorAction(
                    id=f"auto_fix_kb_defaults_{dt.replace(' ', '_').lower()}",
                    type="auto_fix",
                    scope=dt,
                    changes=[{"target": "r2", "doctype": dt, "op": "apply_kb_defaults"}],
                    metadata={"reason": "Inject KB defaults (e.g. naming_series) into mapped payload"},
                )
            )

        if doctypes_for_kb_fix:
            missing_required = [
                f for f in missing_required
                if f not in kb_auto_fields
            ]

        # Missing required fields → LLM-driven message
        if missing_required:
            final_status = "needs_user_input"
            unique_missing = sorted(set(missing_required))

            # Try to get an LLM-enriched explanation
            llm_result = await _call_supervisor_llm(
                gap_analysis={
                    "type": "missing_required_fields",
                    "missing_fields": unique_missing,
                    "node": "validate_mapped_data",
                },
                rag=rag,
                f3iche_id=inp.f3iche_id,
            )

            critical_msg = llm_result.get("critical_message") or (
                f"The following required fields are missing and must be provided before "
                f"import can continue: {', '.join(unique_missing)}. "
                "Please upload a file containing this data or provide the values directly."
            )

            actions.append(
                SupervisorAction(
                    id="ask_user_missing_required_fields",
                    type="ask_user",
                    scope="validation",
                    question=critical_msg,
                    options=["Upload the missing data files", "Provide defaults for warehouse/company fields"],
                    metadata={
                        "missing_required_fields": unique_missing,
                        "tier": "critical",
                    },
                )
            )

    # ══════════════════════════════════════════════════════════════════════════
    # NODE: assess_data_readiness
    # ══════════════════════════════════════════════════════════════════════════
    elif inp.node_name == "assess_data_readiness":
        assessment = (
            (st.primary_result or {}).get("assessment", {})
            if isinstance(st.primary_result, dict)
            else {}
        )

        missing_doctypes = assessment.get("missing_doctypes", []) or []
        partial_doctypes = assessment.get("partial_doctypes", []) or []
        unmappable_chunks = assessment.get("unmappable_chunks", []) or []
        gap_report = assessment.get("gap_report") or {}
        complete_gaps = gap_report.get("complete_gaps") or []

        # Live ERP / LER blocking gaps (single source from readiness agent)
        ler_blocking = [
            g for g in complete_gaps
            if str(g.get("severity", "")).lower() == "blocking"
        ]

        # Two-tier classification (file corpus gaps)
        critical_gaps = [
            g for g in (*missing_doctypes, *partial_doctypes)
            if str(g.get("criticality", "")).lower() == "critical"
            and not bool(g.get("can_proceed_without", False))
        ]
        important_gaps = [
            g for g in (*missing_doctypes, *partial_doctypes)
            if str(g.get("criticality", "")).lower() in ("non_critical",)
            and not bool(g.get("can_proceed_without", True))
        ]
        # "optional" gaps are silently skipped — no action required

        has_critical = bool(critical_gaps) or bool(ler_blocking)
        has_important = bool(important_gaps)

        if has_critical or has_important or ler_blocking:
            gap_summary_for_llm = {
                "critical_gaps": [
                    {
                        "doctype": g.get("doctype", ""),
                        "reason": g.get("reason", ""),
                        "missing_fields": g.get("missing_fields", []),
                        "recommendation": g.get("recommendation", ""),
                    }
                    for g in critical_gaps
                ],
                "important_gaps": [
                    {
                        "doctype": g.get("doctype", ""),
                        "reason": g.get("reason", ""),
                        "recommendation": g.get("recommendation", ""),
                    }
                    for g in important_gaps
                ],
                "unmappable_files": [u.get("filename", "") for u in unmappable_chunks],
            }

            # Call LLM to generate rich natural-language messages
            llm_result = await _call_supervisor_llm(
                gap_analysis=gap_summary_for_llm,
                rag=rag,
                f3iche_id=inp.f3iche_id,
            )

            critical_msg = llm_result.get("critical_message", "")
            important_msg = llm_result.get("important_message", "")

            # Fallback messages if LLM fails
            if not critical_msg and ler_blocking:
                ler_names = ", ".join(
                    g.get("doctype") or g.get("field", "")
                    for g in ler_blocking
                    if g.get("doctype") or g.get("field")
                )
                ler_questions = [g.get("question", "") for g in ler_blocking if g.get("question")]
                critical_msg = (
                    ler_questions[0]
                    if len(ler_questions) == 1
                    else (
                        f"Your live ERP site is missing required masters: {ler_names}. "
                        "Upload data or create records in ERPNext before import."
                    )
                )
            if not critical_msg and critical_gaps:
                critical_doctype_names = ", ".join(
                    g.get("doctype", "") for g in critical_gaps if g.get("doctype")
                )
                critical_msg = (
                    f"We couldn't find data for: {critical_doctype_names}. "
                    "These are required by ERPNext and cannot be skipped — the import will fail without them. "
                    "Please upload files containing this data before we continue."
                )

            if not important_msg and important_gaps:
                important_doctype_names = ", ".join(
                    g.get("doctype", "") for g in important_gaps if g.get("doctype")
                )
                important_msg = (
                    f"We also noticed that {important_doctype_names} are missing. "
                    "Based on your industry, these are strongly recommended before going live. "
                    "You can continue without them today, but you'll need to set them up before production use."
                )

            # CRITICAL action — no "skip" option
            if has_critical:
                final_status = "needs_user_input"
                actions.append(
                    SupervisorAction(
                        id="ask_user_critical_data_missing",
                        type="ask_user",
                        scope="data_readiness_critical",
                        question=critical_msg,
                        options=["Upload the missing files"],
                        metadata={
                            "tier": "critical",
                            "critical_gaps": [
                                {"doctype": g.get("doctype", ""), "reason": g.get("reason", "")}
                                for g in critical_gaps
                            ],
                            "complete_gaps": complete_gaps,
                            "unmappable_chunks": unmappable_chunks,
                        },
                    )
                )

            # IMPORTANT action — user CAN continue but with warning
            if has_important:
                if not has_critical:
                    # Only block if there are no critical gaps making it block already
                    final_status = "needs_user_input"
                actions.append(
                    SupervisorAction(
                        id="ask_user_important_data_recommended",
                        type="ask_user",
                        scope="data_readiness_important",
                        question=important_msg,
                        options=[
                            "Upload recommended files before continuing",
                            "Continue without them (I understand the risk)",
                        ],
                        metadata={
                            "tier": "important",
                            "important_gaps": [
                                {"doctype": g.get("doctype", ""), "reason": g.get("reason", "")}
                                for g in important_gaps
                            ],
                        },
                    )
                )

    # ══════════════════════════════════════════════════════════════════════════
    # NODE: execute_import_phase / preflight_import (execution gate)
    # ══════════════════════════════════════════════════════════════════════════
    elif inp.node_name in ("execute_import_phase", "preflight_import"):
        preflight = (
            (st.primary_result or {}).get("preflight", st.primary_result or {})
            if isinstance(st.primary_result, dict)
            else {}
        )
        preview = preflight.get("confirmation_preview") or {}
        draft_parents = preflight.get("draft_parents") or []
        warnings = preview.get("warnings") or preflight.get("blockers") or []
        high_risk = preview.get("high_risk_doctypes") or []

        if preflight.get("requires_execution_gate") or preflight.get("requires_confirmation"):
            final_status = "needs_user_input"
            question_parts = [preview.get("message") or "Confirm before writing to ERPNext."]
            if draft_parents:
                question_parts.append(
                    f"{len(draft_parents)} draft parent document(s) may block this import."
                )
            if high_risk:
                question_parts.append(
                    f"Financial/high-risk doctypes: {', '.join(high_risk)}."
                )

            actions.append(
                SupervisorAction(
                    id="ask_user_confirm_import_execution",
                    type="ask_user",
                    scope=inp.phase or inp.node_name,
                    question=" ".join(question_parts),
                    options=[
                        "Confirm and run import",
                        "Cancel — review in ERPNext first",
                    ],
                    metadata={
                        "tier": "critical" if high_risk else "important",
                        "preflight": preflight,
                        "warnings": warnings,
                        "draft_parents": draft_parents,
                    },
                )
            )

    retrieved_blocks = ", ".join(sorted([k for k, v in rag.items() if v])) or "none"
    summary = (
        f"{inp.node_name}: status={st.status}, errors={len(st.errors)}, warnings={len(st.warnings)}. "
        f"Retrieved context blocks: {retrieved_blocks}."
    )

    # Safety net: if the workflow is in a non-resolved state but we built zero actions,
    # the UI has nothing to render and the workflow deadlocks waiting for a signal that
    # can never arrive. Add a generic continue action to unblock.
    if not actions and st.status in ("partial", "WARNING", "needs_user_input") and inp.node_name == "assess_data_readiness":
        final_status = "needs_user_input"
        actions.append(
            SupervisorAction(
                id="ask_user_data_readiness_continue",
                type="ask_user",
                scope="data_readiness_continue",
                question=(
                    "Your data has been assessed. Some recommended ERPNext configuration data "
                    "(like Company setup, UOM, Warehouses) may be missing, but ERPNext can "
                    "auto-create defaults for most of these. Would you like to continue with "
                    "what you've provided, or upload additional files first?"
                ),
                options=[
                    "Continue with my current files",
                    "Let me upload more files first",
                ],
                metadata={"tier": "important"},
            )
        )
        activity.logger.info("  Added fallback continue action (no critical gaps detected but status was partial)")

    activity.logger.info(
        "✅ supervise_step done | final_status=%s actions=%d", final_status, len(actions)
    )
    return SupervisorResult(actions=actions, summary_for_ui=summary, final_status=final_status)  # type: ignore[arg-type]


@activity.defn(name="apply_supervisor_actions")
async def apply_supervisor_actions(inp: ApplySupervisorActionsInput) -> ApplyActionsResult:
    """
    Apply auto_fix patches to R2 mapped payloads.
    ask_user actions are handled by the workflow signal loop — not here.
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

                if op == "apply_kb_defaults":
                    from containers.implementation.mapping_agent.defaults import normalize_mapped_payload

                    before = payload.get("records")
                    payload = normalize_mapped_payload(doctype, payload)
                    n = len(payload.get("records") or [])
                    if payload.get("records") != before:
                        await r2_write_json(key, payload, bucket="clean-data")
                        applied.append({"id": act.id, "doctype": doctype, "op": op, "updated": n, "key": key})
                    else:
                        skipped.append({"id": act.id, "doctype": doctype, "reason": "no_changes_after_kb_defaults"})
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
