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
import uuid
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


async def fetch_discovery_context(project_id: str) -> Dict[str, Any]:
    """
    Fetch discovery chat history and metadata from hooks table.
    
    Returns: {
        "chat_history": [...],
        "discovery_metadata": {...},
        "discovery_status": "COMPLETE"|"ACTIVE"|...,
    }
    """
    from sqlalchemy import select
    from shared.database.db import AsyncSessionLocal
    from shared.models.hooks import Hook
    from uuid import UUID
    
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Hook).where(Hook.project_id == UUID(project_id))
            )
            hook = result.scalar_one_or_none()
            
            if not hook:
                return {
                    "chat_history": [],
                    "discovery_metadata": None,
                    "discovery_status": None,
                }
            
            return {
                "chat_history": hook.chat_history or [],
                "discovery_metadata": hook.discovery_metadata or None,
                "discovery_status": hook.discovery_status,
                "discovery_coverage": hook.discovery_coverage,
            }
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not fetch discovery context: %s", e)
        return {
            "chat_history": [],
            "discovery_metadata": None,
            "discovery_status": None,
        }


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

        # Cross-file sanity: filename implies different doctype than assigned
        from containers.implementation.mapping_agent.corpus_merge import (
            filename_conflicts_with_doctype,
            filename_implied_doctype,
        )
        from containers.implementation.supervisor_agent.contract import (
            classify_gap,
            filter_user_gap_messages,
            should_ask_user,
        )

        for check in checks:
            if not isinstance(check, dict):
                continue
            dt = check.get("doctype") or ""
            sources = check.get("source_files") or []
            for src in sources:
                if filename_conflicts_with_doctype(str(src), dt):
                    implied = filename_implied_doctype(str(src))
                    question = (
                        f"File '{src}' looks like {implied or 'another doctype'}, "
                        f"but rows were merged into {dt}. "
                        "Did you mean to map this file to a different ERP document type?"
                    )
                    if classify_gap(question) != "pipeline_fail":
                        final_status = "needs_user_input"
                        actions.append(
                            SupervisorAction(
                                id=f"ask_user_filename_mismatch_{dt}_{src}".replace(" ", "_")[:80],
                                type="ask_user",
                                scope=dt,
                                question=question,
                                options=[
                                    f"Keep as {dt}",
                                    f"Re-classify as {implied}" if implied else "Upload a corrected file",
                                ],
                                metadata={
                                    "tier": "critical",
                                    "source_file": src,
                                    "assigned_doctype": dt,
                                    "implied_doctype": implied,
                                    "gap_class": "user_gap",
                                },
                            )
                        )

        # Empty row value errors → ask_user only when contract says user_gap
        empty_value_msgs: List[str] = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            for err in check.get("errors") or []:
                err_s = str(err)
                if "empty required value" in err_s.lower() or "empty value" in err_s.lower():
                    empty_value_msgs.append(err_s)

        user_empty_msgs = filter_user_gap_messages(empty_value_msgs)
        if user_empty_msgs and should_ask_user(user_empty_msgs):
            final_status = "needs_user_input"
            actions.append(
                SupervisorAction(
                    id="ask_user_empty_identity_values",
                    type="ask_user",
                    scope="validation",
                    question=(
                        "Some rows have empty identity fields (supplier name, item code, etc.). "
                        "Please fix the source file or tell us how to fill these values."
                    ),
                    options=["Upload corrected file", "Apply safe defaults where possible"],
                    metadata={
                        "tier": "critical",
                        "sample_errors": user_empty_msgs[:5],
                        "gap_class": "user_gap",
                    },
                )
            )

        # Missing required fields → LLM-driven message (user_gap only)
        pipeline_only_missing = [
            m for m in missing_required
            if classify_gap(f"Missing required field: {m}") == "pipeline_fail"
        ]
        if pipeline_only_missing and not actions:
            activity.logger.warning(
                "  Pipeline-class gaps only (no ask_user): %s",
                pipeline_only_missing[:5],
            )

        user_missing = [
            m for m in missing_required
            if m not in kb_auto_fields
            and classify_gap(f"Missing required field: {m}") == "user_gap"
        ]
        if user_missing:
            final_status = "needs_user_input"
            unique_missing = sorted(set(user_missing))
            
            # Extract column context from validation report if available
            column_context_parts = []
            for check in checks:
                if not isinstance(check, dict):
                    continue
                dt = check.get("doctype")
                sources = check.get("source_files") or []
                if dt:
                    # Try to get user columns and mapping attempts
                    mapping_methods = (check.get("metadata") or {}).get("mapping_methods") or {}
                    user_cols = (check.get("metadata") or {}).get("user_columns") or []
                    if user_cols:
                        successfully_mapped = [
                            c for c, method in mapping_methods.items()
                            if method in ("kb_local", "llm_column_map", "kb_fuzzy")
                        ]
                        if successfully_mapped:
                            column_context_parts.append(
                                f"{dt} (from {sources[0] if sources else 'uploaded file'}): "
                                f"Successfully mapped {len(successfully_mapped)} columns. "
                                f"Your columns: {', '.join(user_cols[:6])}"
                            )
                        else:
                            column_context_parts.append(
                                f"{dt} (from {sources[0] if sources else 'uploaded file'}): "
                                f"Your columns: {', '.join(user_cols[:6])}"
                            )

            # Try to get an LLM-enriched explanation
            llm_result = await _call_supervisor_llm(
                gap_analysis={
                    "type": "missing_required_fields",
                    "missing_fields": unique_missing,
                    "node": "validate_mapped_data",
                    "column_context": column_context_parts,
                },
                rag=rag,
                f3iche_id=inp.f3iche_id,
            )

            critical_msg = llm_result.get("critical_message")
            if not critical_msg:
                msg_parts = [
                    f"The following required fields are missing and must be provided before import can continue: {', '.join(unique_missing)}."
                ]
                if column_context_parts:
                    msg_parts.append("Column mapping status:")
                    msg_parts.extend(f"  • {ctx}" for ctx in column_context_parts[:3])
                msg_parts.append(
                    "Please upload a file containing this data with column names that match ERPNext field names, "
                    "or provide the values directly."
                )
                critical_msg = " ".join(msg_parts)

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
                        "column_context": column_context_parts,
                    },
                )
            )

        # Blocking LER link misses — auto-create masters during implementation; ask only for true gaps
        ler_gaps = (st.primary_result or {}).get("ler_gaps") if isinstance(st.primary_result, dict) else []
        ler_blocking = [
            g for g in (ler_gaps or [])
            if isinstance(g, dict) and str(g.get("severity", "")).lower() == "blocking"
        ]
        if ler_blocking:
            from containers.implementation.is_common.ler_greenfield import resolve_link_target_doctype

            _MASTER_AUTO = frozenset({"Customer", "Supplier", "Item"})
            master_ler: List[Dict[str, Any]] = []
            user_ler: List[Dict[str, Any]] = []

            for g in ler_blocking:
                meta = g.get("metadata") if isinstance(g.get("metadata"), dict) else {}
                target = resolve_link_target_doctype(
                    {"target_doctype": meta.get("target_doctype"), "field": g.get("field")}
                )
                if target in _MASTER_AUTO:
                    master_ler.append(g)
                else:
                    user_ler.append(g)

            if master_ler:
                actions.append(
                    SupervisorAction(
                        id="auto_fix_transactional_party_stubs",
                        type="auto_fix",
                        scope="validation",
                        changes=[{"target": "r2", "op": "derive_transactional_party_stubs"}],
                        metadata={
                            "reason": "Create Customer/Supplier/Item masters from uploaded transactional refs",
                            "ler_master_count": len(master_ler),
                        },
                    )
                )

            if user_ler:
                final_status = "needs_user_input"
                sample_q = str(user_ler[0].get("question") or "")
                if len(user_ler) == 1 and sample_q:
                    ler_question = sample_q
                else:
                    targets = sorted({
                        str((g.get("metadata") or {}).get("target_doctype") or g.get("field") or "")
                        for g in user_ler
                        if (g.get("metadata") or {}).get("target_doctype") or g.get("field")
                    })
                    ler_question = (
                        "Some link fields could not be resolved: "
                        f"{', '.join(targets) or 'master records'}. "
                        "Reply in chat with how to map or create them, or use + to upload master data."
                    )
                actions.append(
                    SupervisorAction(
                        id="ask_user_ler_blocking_links",
                        type="ask_user",
                        scope="validation",
                        question=ler_question,
                        options=[],
                        metadata={
                            "tier": "critical",
                            "gap_class": "user_gap",
                            "origin": "ler",
                            "chat_only": True,
                            "ler_blocking_count": len(user_ler),
                            "sample_gaps": user_ler[:5],
                        },
                    )
                )

        blocking_mvp = list((st.primary_result or {}).get("blocking_unmapped_seeds") or [])
        if blocking_mvp:
            final_status = "needs_user_input"
            names = ", ".join(blocking_mvp)
            actions.append(
                SupervisorAction(
                    id="ask_user_missing_mvp_files",
                    type="ask_user",
                    scope="validation",
                    question=(
                        f"Your MVP scope still needs uploaded data for: {names}. "
                        "Upload a file for each before we can import to ERPNext."
                    ),
                    options=[
                        "Upload the missing files",
                        "Review my mapped data first",
                    ],
                    metadata={
                        "tier": "critical",
                        "blocking_unmapped_seeds": blocking_mvp,
                        "gap_class": "user_gap",
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
        from containers.implementation.supervisor_agent.gap_consumer import (
            collect_gap_items,
            partition_gaps_for_supervisor,
        )

        gap_items = collect_gap_items(gap_report=gap_report, assessment=assessment)
        complete_gaps = list(gap_report.get("complete_gaps") or [])
        critical_gaps, important_gaps, ler_info_gaps = partition_gaps_for_supervisor(
            gap_items,
            missing_doctypes=missing_doctypes,
            partial_doctypes=partial_doctypes,
        )
        ler_blocking = [
            g for g in gap_items
            if str(g.get("severity", "")).lower() == "blocking"
            and str((g.get("metadata") or {}).get("origin")) in ("live_erp", "ler")
        ]

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
                upload_required = [
                    g for g in critical_gaps
                    if not g.get("can_proceed_without") and not g.get("ready_with_assumptions")
                ]
                critical_doctype_names = ", ".join(
                    g.get("doctype", "") for g in upload_required if g.get("doctype")
                )
                if critical_doctype_names:
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



async def _list_session_mapped_doctypes(session_id: Optional[str]) -> List[str]:
    if not session_id:
        return []
    try:
        import uuid

        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISMappedData
        from sqlalchemy import select

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
    except Exception as e:
        activity.logger.warning("  ⚠ Could not list session mapped doctypes: %s", e)
        return []


async def _apply_vtl_to_payload(
    *,
    act_id: str,
    doctype: str,
    key: str,
    payload: Dict[str, Any],
    overwrite: bool,
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    from containers.implementation.mapping_agent.value_translation import apply_value_translations
    from shared.r2_client import r2_write_json

    records = payload.get("records")
    if not isinstance(records, list):
        return None, {"id": act_id, "doctype": doctype, "reason": "no_records_array", "key": key}

    before = [dict(r) for r in records if isinstance(r, dict)]
    translated, audit = apply_value_translations(doctype, before, overwrite=overwrite)
    if translated == before and not audit:
        return None, {"id": act_id, "doctype": doctype, "reason": "no_vtl_changes", "key": key}

    payload = dict(payload)
    payload["records"] = translated
    await r2_write_json(key, payload, bucket="clean-data")
    return {
        "id": act_id,
        "doctype": doctype,
        "op": "apply_value_translation",
        "updated": len(translated),
        "translations": len(audit),
        "key": key,
    }, None


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

            op = ch.get("op")
            overwrite = bool(ch.get("overwrite", True))

            if op == "apply_user_note_resolutions":
                from containers.implementation.supervisor_agent.user_note_resolutions import (
                    apply_user_note_resolutions,
                )

                note = str((act.metadata or {}).get("user_note") or "")
                sample_gaps = (act.metadata or {}).get("sample_gaps")
                if not isinstance(sample_gaps, list):
                    sample_gaps = []
                result = await apply_user_note_resolutions(
                    session_id=inp.session_id,
                    project_id=inp.project_id,
                    company_slug=company_slug,
                    user_note=note,
                    sample_gaps=sample_gaps,
                )
                if result.get("status") == "ok" and result.get("written", 0) > 0:
                    applied.append({
                        "id": act.id,
                        "op": op,
                        "written": result.get("written"),
                        "audit": result.get("audit"),
                    })
                elif result.get("status") == "ok":
                    skipped.append({"id": act.id, "reason": "no_payload_changes", "audit": result.get("audit")})
                else:
                    skipped.append({"id": act.id, "reason": result.get("status", "unknown")})
                continue

            if op == "apply_value_translation" and not ch.get("doctype"):
                from shared.r2_client import r2_read_json

                for dt in await _list_session_mapped_doctypes(inp.session_id):
                    key = f"{company_slug}/{inp.project_id}/mappings/mapped_payloads/{dt}.json"
                    try:
                        payload = await r2_read_json(key, bucket="clean-data") or {}
                        result, skip = await _apply_vtl_to_payload(
                            act_id=act.id,
                            doctype=dt,
                            key=key,
                            payload=payload,
                            overwrite=overwrite,
                        )
                        if result:
                            applied.append(result)
                        elif skip:
                            skipped.append(skip)
                    except Exception as e:
                        errors.append({"id": act.id, "doctype": dt, "error": str(e), "key": key})
                continue

            if op == "derive_transactional_party_stubs":
                from containers.implementation.is_common.transactional_party_stubs import (
                    derive_transactional_party_masters,
                )
                from shared.r2_client import r2_read_json, r2_write_json

                mapped_data: Dict[str, Any] = {}
                for dt in await _list_session_mapped_doctypes(inp.session_id):
                    key = f"{company_slug}/{inp.project_id}/mappings/mapped_payloads/{dt}.json"
                    try:
                        payload = await r2_read_json(key, bucket="clean-data") or {}
                        if isinstance(payload, dict):
                            mapped_data[dt] = payload
                    except Exception as e:
                        errors.append({"id": act.id, "doctype": dt, "error": str(e), "key": key})

                if not mapped_data:
                    skipped.append({"id": act.id, "reason": "no_mapped_payloads"})
                    continue

                enriched, audit = derive_transactional_party_masters(mapped_data)
                for dt, payload in enriched.items():
                    before = mapped_data.get(dt) or {}
                    if payload.get("records") == before.get("records"):
                        continue
                    key = f"{company_slug}/{inp.project_id}/mappings/mapped_payloads/{dt}.json"
                    try:
                        await r2_write_json(key, payload, bucket="clean-data")
                        applied.append({
                            "id": act.id,
                            "doctype": dt,
                            "op": op,
                            "updated": len(payload.get("records") or []),
                            "key": key,
                        })
                    except Exception as e:
                        errors.append({"id": act.id, "doctype": dt, "error": str(e), "key": key})
                if audit and not any(a.get("op") == op for a in applied):
                    applied.append({"id": act.id, "op": op, "stubs": audit})
                elif not audit:
                    skipped.append({"id": act.id, "reason": "no_party_stubs_added"})
                continue

            if op == "create_party_stub":
                from containers.implementation.is_common.transactional_party_stubs import (
                    inject_party_master_stub,
                )
                from shared.r2_client import r2_read_json, r2_write_json

                party_name = ch.get("name") or (act.metadata or {}).get("name")
                master_dt = str(ch.get("doctype") or act.scope or "Customer")
                if not party_name:
                    skipped.append({"id": act.id, "reason": "missing_party_name"})
                    continue

                mapped_data = {}
                for dt in await _list_session_mapped_doctypes(inp.session_id):
                    key = f"{company_slug}/{inp.project_id}/mappings/mapped_payloads/{dt}.json"
                    try:
                        payload = await r2_read_json(key, bucket="clean-data") or {}
                        if isinstance(payload, dict):
                            mapped_data[dt] = payload
                    except Exception as e:
                        errors.append({"id": act.id, "doctype": dt, "error": str(e), "key": key})

                enriched, changed = inject_party_master_stub(
                    mapped_data,
                    master_doctype=master_dt,
                    name=str(party_name),
                )
                if not changed:
                    skipped.append({"id": act.id, "doctype": master_dt, "reason": "party_stub_unchanged"})
                    continue
                target_payload = enriched.get(master_dt)
                if not isinstance(target_payload, dict):
                    skipped.append({"id": act.id, "doctype": master_dt, "reason": "no_target_payload"})
                    continue
                target_key = f"{company_slug}/{inp.project_id}/mappings/mapped_payloads/{master_dt}.json"
                await r2_write_json(target_key, target_payload, bucket="clean-data")
                applied.append({
                    "id": act.id,
                    "doctype": master_dt,
                    "op": op,
                    "name": party_name,
                    "key": target_key,
                })
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

                if op == "apply_value_translation":
                    result, skip = await _apply_vtl_to_payload(
                        act_id=act.id,
                        doctype=doctype,
                        key=key,
                        payload=payload,
                        overwrite=overwrite,
                    )
                    if result:
                        applied.append(result)
                    elif skip:
                        skipped.append(skip)
                    continue

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

    if applied:
        try:
            from containers.implementation.file_io.persist_chat_message import (
                format_auto_fix_chat_message,
                save_chat_message,
            )
            from shared.database.db import AsyncSessionLocal
            from shared.models.is_models import ISSession

            content = format_auto_fix_chat_message(applied)
            if content:
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import select

                    row = (
                        await session.execute(
                            select(ISSession).where(
                                ISSession.project_id == uuid.UUID(inp.project_id)
                            ).order_by(ISSession.created_at.desc()).limit(1)
                        )
                    ).scalar_one_or_none()
                if row:
                    step = inp.step if inp.step in ("upload", "analyze", "validate", "import") else "validate"
                    await save_chat_message(
                        str(row.id),
                        step,
                        "system",
                        content,
                        message_type="auto_fix_applied",
                        message_metadata={"applied": applied, "step": inp.step},
                    )
        except Exception as e:
            activity.logger.warning("  ⚠ Could not persist auto-fix chat message: %s", e)

    return ApplyActionsResult(applied=applied, skipped=skipped, errors=errors)
