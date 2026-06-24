"""
IS Chat Dispatcher — routes free-text user messages to the right handler.

Phase 1: intent classification + refine_mapping / general Q&A / upload guidance.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from shared.database.db import AsyncSessionLocal
from shared.models.core import Project
from shared.models.is_models import (
    ISChatMessage,
    ISDataReadinessAssessment,
    ISSession,
    ISSupervisorPrompt,
    ISValidationError,
    ISValidationResult,
)
from containers.implementation.file_io.persist_chat_message import save_chat_message
from containers.implementation.mapping_agent.activities import (
    RefineMappingInput,
    refine_mapping_with_llm,
)
from shared.shared_llm import generate_json

logger = logging.getLogger(__name__)

_REMAP_PATTERNS = re.compile(
    r"\b(map|mapping|column|field|rename|remap|change\s+.+\s+to)\b",
    re.I,
)
_UPLOAD_PATTERNS = re.compile(
    r"\b(upload|attach|missing\s+file|add\s+file|send\s+file)\b",
    re.I,
)
_LINK_VALUE_ANSWER = re.compile(
    r"\b(?:use|means?|should\s+be|call\s+it|map\s+(?:to|as))\s+(?:the\s+)?([A-Za-z][\w\s./&-]{1,40})",
    re.I,
)
_CREATE_MASTER = re.compile(
    r"\b(?:create|add|make|register)\s+(?:a\s+|the\s+|new\s+)?(customer|supplier|item)\b",
    re.I,
)
_CREATE_MASTER_NAME = re.compile(
    r"(?:customer|supplier|item)\s*[-–—:]\s*([A-Za-z0-9][\w\s.&/-]{1,80})",
    re.I,
)
_CONTINUE_PATTERNS = re.compile(
    r"\b(continue|proceed|yes|skip|confirm|go\s+ahead|use\s+defaults?)\b",
    re.I,
)
_MAPPING_RULES = re.compile(
    r"(?:^\s*\d+\.|treat\s+(?:this|rows|as)|map\s+\w+\s+to\s+\w+|translation\s+rules|strict\s+.*\s+rules)",
    re.I | re.M,
)

CHAT_INTENT_PROMPT = """You are the Implementation Assistant for an ERP data import pipeline.

SESSION CONTEXT (JSON):
{context_json}

OPEN SUPERVISOR PROMPTS (if any):
{open_prompts_json}

USER MESSAGE:
{message}

Classify the user's intent and respond appropriately.

Return JSON only:
{{
  "intent": "remap" | "upload_intent" | "answer_supervisor" | "general_question" | "mapping_rules",
  "reply": "assistant reply text (required for general_question and upload_intent; for remap leave empty)",
  "confidence": 0.0 to 1.0
}}

Rules:
- "remap": user wants to change how a spreadsheet column maps to an ERP field (e.g. "map party_name to supplier_name").
- "upload_intent": user wants to upload or add files.
- "answer_supervisor": user is answering an open supervisor question (continue, upload, confirm, or free-text note).
- "mapping_rules": user provides structured file→doctype translation rules for a re-run (numbered list, Tally rules, etc.).
- Be concise, honest, and refer to actual context — do not invent row counts or doctype names not in context.
"""


async def _get_company_slug(project_id: str) -> str:
    async with AsyncSessionLocal() as session:
        proj = (
            await session.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        return proj.company_slug if proj and proj.company_slug else "unknown"


async def build_session_context(
    is_session: ISSession,
    step: str,
) -> Dict[str, Any]:
    """Assemble context for chat intent routing and general Q&A."""
    ctx: Dict[str, Any] = {
        "session_id": str(is_session.id),
        "project_id": str(is_session.project_id),
        "workflow_status": is_session.status,
        "step": step,
        "user_import_note": is_session.user_import_note,
    }

    async with AsyncSessionLocal() as session:
        readiness = (
            await session.execute(
                select(ISDataReadinessAssessment)
                .where(ISDataReadinessAssessment.session_id == is_session.id)
                .order_by(ISDataReadinessAssessment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if readiness:
            ctx["data_readiness"] = {
                "score": readiness.import_readiness_score,
                "missing_doctypes": readiness.missing_doctypes or [],
                "partial_doctypes": readiness.partial_doctypes or [],
                "executive_summary": readiness.executive_summary,
            }

        val_rows = (
            await session.execute(
                select(ISValidationResult)
                .where(ISValidationResult.session_id == is_session.id)
                .limit(50)
            )
        ).scalars().all()

        vr_ids = [vr.id for vr in val_rows]
        errors_by_vr_id: Dict[Any, List[Any]] = {}
        if vr_ids:
            err_rows = (
                await session.execute(
                    select(ISValidationError)
                    .where(ISValidationError.validation_result_id.in_(vr_ids))
                    .limit(500)
                )
            ).scalars().all()
            for e in err_rows:
                errors_by_vr_id.setdefault(e.validation_result_id, []).append(e)

        validation_summary: List[Dict[str, Any]] = []
        for vr in val_rows:
            errors = errors_by_vr_id.get(vr.id, [])
            validation_summary.append(
                {
                    "doctype": vr.doctype,
                    "status": vr.overall_status,
                    "errors": [e.error_message for e in errors if e.severity == "error"][:5],
                    "warnings": [e.error_message for e in errors if e.severity == "warning"][:5],
                }
            )
        if validation_summary:
            ctx["validation"] = validation_summary

    from app.services.is_launcher import ImplementationLauncher

    launcher = ImplementationLauncher()
    full_report = await launcher.get_validation_report(str(is_session.project_id))
    if full_report:
        ctx["validation_report"] = full_report

    corpus = await launcher.get_corpus_assignments(str(is_session.project_id))
    if corpus:
        ctx["corpus_assignments"] = corpus

    import_plan = await launcher.get_import_plan(str(is_session.project_id))
    if import_plan:
        ctx["import_plan"] = {
            "status": import_plan.get("plan_status") or import_plan.get("status"),
            "blocked_reasons": import_plan.get("blocked_reasons") or [],
            "optional_gaps": import_plan.get("optional_gaps") or [],
        }

    async with AsyncSessionLocal() as session:
        open_prompts = (
            await session.execute(
                select(ISSupervisorPrompt)
                .where(ISSupervisorPrompt.session_id == is_session.id)
                .where(ISSupervisorPrompt.status == "open")
                .order_by(ISSupervisorPrompt.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        if open_prompts:
            ctx["open_supervisor_prompts"] = [
                {
                    "id": str(p.id),
                    "step": p.step,
                    "summary": p.summary_for_ui,
                    "actions": p.actions or [],
                }
                for p in open_prompts
            ]

    return ctx


def _heuristic_intent(message: str) -> Optional[str]:
    if _looks_like_mapping_rules(message):
        return "mapping_rules"
    if _REMAP_PATTERNS.search(message):
        return "remap"
    if _UPLOAD_PATTERNS.search(message):
        return "upload_intent"
    return None


def _looks_like_mapping_rules(message: str) -> bool:
    """Multi-line mapping instructions (e.g. Gemini Tally translation rules)."""
    text = (message or "").strip()
    if len(text) < 120:
        return False
    hits = len(_MAPPING_RULES.findall(text))
    return hits >= 2 or (hits >= 1 and len(text) > 400)


def _looks_like_link_value_answer(message: str, context: Dict[str, Any]) -> bool:
    """Free-text answers like 'use litre' while validation/LER prompts are open."""
    if not (context.get("open_supervisor_prompts") or context.get("validation")):
        return False
    if _LINK_VALUE_ANSWER.search(message):
        return True
    stripped = message.strip()
    if len(stripped) <= 32 and not _REMAP_PATTERNS.search(message):
        validation = context.get("validation") or []
        blob = json.dumps(validation, default=str).lower()
        if any(token in blob for token in ("uom", "link", "unresolvable", "not found")):
            return True
    return False


async def _classify_intent(
    message: str,
    context: Dict[str, Any],
) -> Tuple[str, str]:
    """Return (intent, optional_reply)."""
    hint = _heuristic_intent(message)
    if hint == "remap":
        return "remap", ""

    open_prompts = context.get("open_supervisor_prompts") or []
    try:
        result = generate_json(
            CHAT_INTENT_PROMPT.format(
                context_json=json.dumps(context, default=str)[:8000],
                open_prompts_json=json.dumps(open_prompts, default=str)[:4000],
                message=message,
            ),
            temperature=0.1,
            max_output_tokens=800,
        )
        intent = str(result.get("intent") or "general_question")
        reply = str(result.get("reply") or "")
        if intent not in ("remap", "upload_intent", "answer_supervisor", "general_question", "mapping_rules"):
            intent = "general_question"
        return intent, reply
    except Exception as e:
        logger.warning("Chat intent LLM failed, using heuristics: %s", e)
        if hint:
            return hint, ""
        return "general_question", (
            "I couldn't process that fully right now. "
            "Try asking about a specific mapping change (e.g. 'map vendor_name to supplier_name') "
            "or describe a validation issue you see on screen."
        )


def _match_supervisor_option(message: str, options: List[str]) -> Optional[str]:
    msg = message.strip().lower()
    if not options:
        return None
    for opt in options:
        if msg == opt.strip().lower() or msg in opt.strip().lower():
            return opt
    if any(w in msg for w in ("continue", "proceed", "yes", "ok", "skip")):
        for opt in options:
            if "continue" in opt.lower() or "anyway" in opt.lower():
                return opt
    if any(w in msg for w in ("upload", "attach", "file")):
        for opt in options:
            if "upload" in opt.lower():
                return opt
    return options[0] if len(options) == 1 else None


def _extract_create_master(message: str, action: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Parse chat intent to create a Customer/Supplier/Item master during implementation."""
    if not _CREATE_MASTER.search(message):
        return None

    meta = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
    sample_gaps = meta.get("sample_gaps") if isinstance(meta.get("sample_gaps"), list) else []
    gap = sample_gaps[0] if sample_gaps and isinstance(sample_gaps[0], dict) else {}

    gap_meta = gap.get("metadata") if isinstance(gap.get("metadata"), dict) else {}
    name = str(gap_meta.get("value") or gap.get("value") or "").strip()
    doctype = str(gap_meta.get("target_doctype") or gap.get("field") or "Customer").strip()
    if doctype.lower() in ("customer", "supplier", "item"):
        doctype = doctype.title() if doctype.lower() != "item" else "Item"
    elif doctype.lower() == "customer":
        doctype = "Customer"
    elif doctype.lower() == "supplier":
        doctype = "Supplier"

    match = _CREATE_MASTER.search(message)
    if match:
        spoken = match.group(1).lower()
        if spoken == "customer":
            doctype = "Customer"
        elif spoken == "supplier":
            doctype = "Supplier"
        elif spoken == "item":
            doctype = "Item"

    name_match = _CREATE_MASTER_NAME.search(message)
    if name_match:
        name = name_match.group(1).strip(" .!")

    if not name:
        quoted = re.search(r"['\"]([^'\"]{2,80})['\"]", message)
        if quoted:
            name = quoted.group(1).strip()

    if not name or doctype not in ("Customer", "Supplier", "Item"):
        return None
    return {"doctype": doctype, "name": name}


async def _handle_supervisor_answer(
    is_session: ISSession,
    message: str,
    step: str,
    open_prompts: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not open_prompts:
        return None

    prompt = open_prompts[0]
    actions = prompt.get("actions") or []
    ask_actions = [a for a in actions if isinstance(a, dict) and a.get("type") == "ask_user"]
    if not ask_actions:
        return None

    action = ask_actions[0]
    action_id = str(action.get("id") or "")
    if not action_id:
        return None

    options = [str(o) for o in (action.get("options") or []) if o]
    selected = _match_supervisor_option(message, options) if options else None

    create_master = _extract_create_master(message, action)
    extra_data: Dict[str, Any] = {"user_note": message}
    if selected:
        extra_data["selected_option"] = selected
    if create_master:
        extra_data["create_master"] = create_master
        extra_data["create_master_intent"] = True

    link_match = _LINK_VALUE_ANSWER.search(message)
    if not selected and not create_master and link_match and options:
        for opt in options:
            if "default" in opt.lower() or "continue" in opt.lower():
                selected = opt
                extra_data["selected_option"] = selected
                break

    from app.services.is_launcher import ImplementationLauncher

    launcher = ImplementationLauncher()
    await launcher.answer_supervisor_prompt(
        is_session.project_id,
        str(prompt.get("id")),
        action_id,
        extra_data=extra_data,
    )

    if create_master:
        content = (
            f"Understood — I'll add {create_master['doctype']} "
            f"\"{create_master['name']}\" from your upload and re-run validation."
        )
    else:
        content = (
            "Got it — I've sent your response to the workflow"
            + (f' (option: "{selected}")' if selected else "")
            + ". The pipeline will continue shortly."
        )
    msg_id = await save_chat_message(
        str(is_session.id),
        step,
        "assistant",
        content,
        message_type="chat",
        message_metadata={"supervisor_answer": True, "prompt_id": prompt.get("id")},
    )
    return {
        "id": msg_id,
        "role": "assistant",
        "content": content,
        "message_type": "chat",
        "metadata": {"supervisor_answer": True},
    }


async def _handle_mapping_rules(
    is_session: ISSession,
    message: str,
    step: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist structured mapping rules for the next mapping pass."""
    from sqlalchemy import update

    workflow_status = str(context.get("workflow_status") or "")
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(select(ISSession).where(ISSession.id == is_session.id))
        ).scalar_one_or_none()
        if row:
            notes = list(row.user_notes or [])
            notes.append({
                "type": "mapping_rules",
                "step": step,
                "note": message[:8000],
                "answered_at": datetime.utcnow().isoformat() + "Z",
            })
            await session.execute(
                update(ISSession)
                .where(ISSession.id == is_session.id)
                .values(
                    user_import_note=message[:8000],
                    user_notes=notes,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()

    if workflow_status == "awaiting_validation_submission":
        content = (
            "I've saved your mapping rules for this session.\n\n"
            "Mapping has **already completed** for this run — the worker is waiting for you to "
            "**review and submit on the Validate page** (not chat).\n\n"
            "Your rules will apply on the **next upload or fresh implementation run**. "
            "For this run, use the Validate view to confirm or edit what was mapped."
        )
    elif workflow_status.startswith("awaiting_"):
        content = (
            "I've saved your mapping rules. They'll be applied when the pipeline reaches "
            "file mapping in this session.\n\n"
            "If mapping already failed for specific files, you may still need to fix column "
            "headers or re-upload after this run completes."
        )
    else:
        content = (
            "I've saved your mapping rules to this session.\n\n"
            "They'll be used during the next **mapping** step. "
            "If you need them applied immediately, start a new implementation run with the same files."
        )

    msg_id = await save_chat_message(
        str(is_session.id),
        step,
        "assistant",
        content,
        message_type="chat",
        message_metadata={"mapping_rules_saved": True},
    )
    return {
        "id": msg_id,
        "role": "assistant",
        "content": content,
        "message_type": "chat",
        "metadata": {"mapping_rules_saved": True},
    }


async def _handle_remap(
    is_session: ISSession,
    message: str,
    step: str,
    company_slug: str,
) -> Dict[str, Any]:
    result = await refine_mapping_with_llm(
        RefineMappingInput(
            session_id=str(is_session.id),
            user_feedback=message,
            project_id=str(is_session.project_id),
            company_slug=company_slug,
        )
    )

    if result.get("error"):
        content = "I couldn't update the mapping right now. Please try again or use the validate table to review current mappings."
        meta = {"error": result.get("error")}
    elif result.get("status") == "no_mappings_found":
        content = "There are no field mappings yet for this session. Upload and analyze your files first, then ask me to adjust mappings."
        meta = result
    else:
        changes = result.get("changes_count", 0)
        updated = result.get("updated_mappings") or []
        if changes == 0:
            content = "I reviewed your request but didn't find mapping changes to apply. Try being specific, e.g. 'map party_name to supplier_name for Supplier'."
        else:
            lines = []
            for u in updated[:5]:
                col = u.get("source_column") or "?"
                field = u.get("new_target_field") or u.get("target_field") or "?"
                lines.append(f"• `{col}` → `{field}`")
            extra = f"\n…and {len(updated) - 5} more." if len(updated) > 5 else ""
            content = (
                f"Updated {changes} mapping(s) based on your request:\n"
                + "\n".join(lines)
                + extra
                + "\n\nRefresh the validate preview to see the effect."
            )
        meta = {"refine_result": result}

    msg_id = await save_chat_message(
        str(is_session.id),
        step,
        "assistant",
        content,
        message_type="chat",
        message_metadata=meta,
    )
    return {
        "id": msg_id,
        "role": "assistant",
        "content": content,
        "message_type": "chat",
        "metadata": meta,
    }


async def dispatch_chat_message(
    is_session: ISSession,
    message: str,
    step: str,
) -> Dict[str, Any]:
    """
    Persist user message, route by intent, persist and return assistant response.
    """
    message = (message or "").strip()
    if not message:
        raise ValueError("Message cannot be empty")
    if len(message) > 8000:
        raise ValueError("Message too long (max 8000 characters)")

    step = step if step in ("upload", "analyze", "validate", "import") else "analyze"

    await save_chat_message(
        str(is_session.id),
        step,
        "user",
        message,
        message_type="chat",
    )

    context = await build_session_context(is_session, step)
    open_prompts = context.get("open_supervisor_prompts") or []
    intent, llm_reply = await _classify_intent(message, context)
    company_slug = await _get_company_slug(str(is_session.project_id))

    if open_prompts and not _looks_like_mapping_rules(message) and (
        intent == "answer_supervisor"
        or _CREATE_MASTER.search(message)
        or _looks_like_link_value_answer(message, context)
        or (intent == "upload_intent" and _UPLOAD_PATTERNS.search(message))
        or (intent != "mapping_rules" and _CONTINUE_PATTERNS.search(message))
    ):
        supervisor_reply = await _handle_supervisor_answer(
            is_session, message, step, open_prompts
        )
        if supervisor_reply:
            return supervisor_reply

    if intent == "mapping_rules":
        return await _handle_mapping_rules(is_session, message, step, context)

    if intent == "remap" and not _looks_like_link_value_answer(message, context):
        return await _handle_remap(is_session, message, step, company_slug)

    if intent == "upload_intent":
        content = llm_reply or (
            "You can upload files using the upload area on the left, or use the "
            "**Upload missing files** button when the assistant flags a gap. "
            "After upload, I'll re-scan and update the analysis."
        )
    else:
        content = llm_reply or (
            "I'm here to help with mapping, validation, and import questions. "
            "Ask about a specific column, doctype, or error message you see."
        )

    msg_id = await save_chat_message(
        str(is_session.id),
        step,
        "assistant",
        content,
        message_type="chat",
        message_metadata={"intent": intent},
    )
    return {
        "id": msg_id,
        "role": "assistant",
        "content": content,
        "message_type": "chat",
        "metadata": {"intent": intent},
    }


async def get_chat_messages(
    session_id: str,
    *,
    step: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    import uuid as uuid_mod

    sid = uuid_mod.UUID(session_id)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISChatMessage)
            .where(ISChatMessage.session_id == sid)
            .order_by(ISChatMessage.created_at.asc())
            .limit(limit)
        )
        if step:
            stmt = stmt.where(ISChatMessage.step == step)
        rows = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": str(r.id),
                "session_id": str(r.session_id),
                "step": r.step,
                "role": r.role,
                "content": r.content,
                "message_type": r.message_type,
                "metadata": r.message_metadata or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
