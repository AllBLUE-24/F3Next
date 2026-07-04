"""
Synchronous discovery chat — DB orchestration (no Temporal).

Step 1: Discovery Assistant — chat → MVP/target draft → workflow preview → confirm → upload.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from containers.discovery.chat_service import (
    MAX_USER_TURNS,
    _utc_now_iso,
    complete_discovery,
    count_user_turns,
    generate_chat_reply,
    normalize_messages,
    opening_messages,
    transcript_text,
)
from containers.discovery.f3iche_resolver import resolve_discovery_f3iche_niche
from containers.discovery.phases import DiscoveryPhase, get_phase, is_upload_ready
from containers.discovery.workflow_explanation import generate_workflow_explanation
from containers.discovery.target.persist import generate_project_target_structure
from shared.models.core import Project
from shared.models.hooks import Hook
from shared.models.project_target import ProjectTargetStructure


async def get_or_create_hook(db: AsyncSession, project_id: UUID) -> Hook:
    result = await db.execute(select(Hook).where(Hook.project_id == project_id))
    hook = result.scalar_one_or_none()

    if hook:
        return hook

    hook = Hook(
        project_id=project_id,
        discovery_status="ACTIVE",
        discovery_step=1,
        discovery_turn_count=0,
        discovery_coverage=None,
        extracted_tags=[],
        chat_history=opening_messages(),
        last_bot_response=opening_messages()[0]["content"],
        answers_health_check={},
        report_content="",
    )
    db.add(hook)
    await db.commit()
    await db.refresh(hook)
    return hook


def _ensure_opening(hook: Hook) -> list[dict]:
    messages = normalize_messages(hook.chat_history)
    if not messages:
        messages = opening_messages()
    return messages


def _session_payload(hook: Hook, messages: list[dict]) -> dict:
    user_turns = count_user_turns(messages)
    metadata = hook.discovery_metadata or {}
    phase = get_phase(metadata)
    finalized = is_upload_ready(metadata)
    awaiting_confirmation = phase in (
        DiscoveryPhase.WORKFLOW_DISPLAY,
        DiscoveryPhase.MODULE_CONFIRMATION,
    )

    return {
        "messages": messages,
        "status": hook.discovery_status or "ACTIVE",
        "phase": phase.value,
        "is_complete": finalized,
        "is_finalized": finalized,
        "awaiting_confirmation": awaiting_confirmation,
        "user_turns": user_turns,
        "ready_for_recommendation": user_turns >= 2 and hook.discovery_status != "COMPLETE",
        "discovery_metadata": metadata if metadata else None,
        "coverage": hook.discovery_coverage,
    }


async def load_session(db: AsyncSession, project_id: UUID) -> dict:
    hook = await get_or_create_hook(db, project_id)
    messages = _ensure_opening(hook)

    if normalize_messages(hook.chat_history) != messages:
        hook.chat_history = messages
        hook.last_bot_response = messages[-1]["content"] if messages else ""
        hook.discovery_status = hook.discovery_status or "ACTIVE"
        await db.commit()

    return _session_payload(hook, messages)


async def send_chat_message(db: AsyncSession, project_id: UUID, user_message: str) -> dict:
    hook = await get_or_create_hook(db, project_id)

    if hook.discovery_status == "COMPLETE":
        return {
            "reply": "Discovery is already complete. Head to your recommendation to continue.",
            "messages": normalize_messages(hook.chat_history),
            "status": "COMPLETE",
            "phase": DiscoveryPhase.FINALIZED.value,
            "is_complete": True,
            "is_finalized": True,
            "ready_for_recommendation": False,
        }

    if hook.discovery_status == "AWAITING_CONFIRMATION":
        return {
            "reply": (
                "Your recommendation is ready. Please review the implementation workflow "
                "and confirm the modules on the recommendation page."
            ),
            "messages": normalize_messages(hook.chat_history),
            "status": hook.discovery_status,
            "phase": get_phase(hook.discovery_metadata).value,
            "is_complete": False,
            "is_finalized": False,
            "ready_for_recommendation": False,
        }

    messages = _ensure_opening(hook)
    user_turns = count_user_turns(messages)

    if user_turns >= MAX_USER_TURNS:
        return {
            "reply": (
                "We've covered a lot — I think I have enough to work with. "
                "Hit 'Get my ERP recommendation' when you're ready!"
            ),
            "messages": messages,
            "status": hook.discovery_status,
            "phase": DiscoveryPhase.INITIAL_CHAT.value,
            "is_complete": False,
            "is_finalized": False,
            "ready_for_recommendation": True,
            "user_turns": user_turns,
        }

    messages.append({
        "role": "user",
        "content": user_message.strip(),
        "ts": _utc_now_iso(),
    })

    reply = await generate_chat_reply(messages)

    messages.append({
        "role": "assistant",
        "content": reply,
        "ts": _utc_now_iso(),
    })

    user_turns = count_user_turns(messages)

    hook.chat_history = messages
    hook.last_bot_response = reply
    hook.discovery_turn_count = user_turns
    hook.discovery_status = "ACTIVE"
    await db.commit()

    return {
        "reply": reply,
        "messages": messages,
        "status": "ACTIVE",
        "phase": DiscoveryPhase.INITIAL_CHAT.value,
        "is_complete": False,
        "is_finalized": False,
        "user_turns": user_turns,
        "ready_for_recommendation": user_turns >= 2,
    }


async def _get_project(db: AsyncSession, project_id: UUID) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError(f"Project not found: {project_id}")
    if not project.company_slug:
        raise ValueError("Project missing company_slug")
    return project


async def finalize_discovery(db: AsyncSession, project_id: UUID) -> dict:
    """End chat, generate MVP/target draft + workflow preview (not finalized yet)."""
    hook = await get_or_create_hook(db, project_id)
    metadata = hook.discovery_metadata or {}
    phase = get_phase(metadata)

    if phase == DiscoveryPhase.FINALIZED and hook.discovery_status == "COMPLETE":
        return {
            "status": "ready",
            "phase": phase.value,
            "data": metadata,
            "coverage": hook.discovery_coverage,
            "extracted_tags": hook.extracted_tags or [],
        }

    if phase in (DiscoveryPhase.WORKFLOW_DISPLAY, DiscoveryPhase.MODULE_CONFIRMATION):
        return {
            "status": "awaiting_confirmation",
            "phase": phase.value,
            "data": metadata,
            "coverage": hook.discovery_coverage,
            "extracted_tags": hook.extracted_tags or [],
            "confirmation_message": metadata.get("workflow_explanation", {}).get(
                "workflow_summary",
                "Review your implementation workflow on the next screen.",
            ),
        }

    messages = normalize_messages(hook.chat_history)
    if count_user_turns(messages) < 1:
        raise ValueError("Need at least one exchange before generating a recommendation.")

    result = await complete_discovery(messages)

    broad_f3iche = result["discovery_metadata"].get("f3iche", "trading")
    industry = result["discovery_metadata"].get("industry", "")
    mvp_focus = result["discovery_metadata"].get("mvp_focus") or {}
    bottleneck = mvp_focus.get("primary_bottleneck", "")

    niche_id = resolve_discovery_f3iche_niche(
        discovery_f3iche=broad_f3iche,
        industry=industry,
        chat_transcript=transcript_text(messages),
    )

    discovery_metadata = {
        **result["discovery_metadata"],
        "f3iche_niche": niche_id,
        "phase": DiscoveryPhase.WORKFLOW_DISPLAY.value,
    }

    # Persist metadata before target generation (post_discovery_service reads hooks.discovery_metadata)
    hook.discovery_coverage = result["coverage"]
    hook.extracted_tags = result["extracted_tags"]
    hook.discovery_metadata = discovery_metadata
    await db.flush()

    project = await _get_project(db, project_id)
    target_payload = await generate_project_target_structure(
        db=db,
        project_id=project_id,
        company_slug=project.company_slug,
    )

    target_structure = target_payload.get("target_structure") or {}
    scoping = target_structure.get("scoping") or {}
    deferred_seeds = target_payload.get("deferred_doctypes") or target_structure.get("deferred_doctypes") or []

    workflow_explanation = await generate_workflow_explanation(
        f3iche=niche_id,
        industry=industry,
        bottleneck=bottleneck,
        target_structure=target_structure or {},
        coverage=result["coverage"],
        chat_transcript=transcript_text(messages),
        mvp_focus=mvp_focus,
        deferred_seeds=deferred_seeds,
        dual_system_note=scoping.get("dual_system_note", ""),
        scoping_reasoning=scoping.get("scoping_reasoning", ""),
    )

    # New dict + flag_modified — in-place JSON mutations are not persisted by SQLAlchemy
    discovery_metadata = {
        **discovery_metadata,
        "target_structure": {
            "seed_doctypes": target_payload.get("seed_doctypes", []),
            "deferred_doctypes": deferred_seeds,
            "required_doctypes": target_payload.get("required_doctypes", []),
            "setup_steps": target_structure.get("setup_steps", []),
            "import_phases": target_structure.get("import_phases", {}),
            "target_structure_id": target_payload.get("target_structure_id"),
            "mvp_boundary_id": target_payload.get("mvp_boundary_id"),
            "scoping_mode": scoping.get("scoping_mode"),
            "scoping_reasoning": scoping.get("scoping_reasoning"),
            "dual_system_note": scoping.get("dual_system_note"),
        },
        "workflow_explanation": workflow_explanation,
        "phase": DiscoveryPhase.MODULE_CONFIRMATION.value,
    }

    headline = result["discovery_metadata"].get("headline", "")
    confirmation_message = (
        f"Perfect! Based on our conversation, you're a **{_format_f3iche(broad_f3iche)}** business "
        f"in the {industry or 'your'} industry. {headline}\n\n"
        f"{workflow_explanation.get('workflow_summary', '')}\n\n"
        "Next: review the modules and files we'll need before you upload data."
    )

    messages.append({
        "role": "assistant",
        "content": confirmation_message,
        "ts": _utc_now_iso(),
    })

    hook.chat_history = messages
    hook.discovery_metadata = discovery_metadata
    flag_modified(hook, "discovery_metadata")
    hook.discovery_status = "AWAITING_CONFIRMATION"
    hook.discovery_turn_count = count_user_turns(messages)
    hook.last_bot_response = confirmation_message
    await db.commit()

    return {
        "status": "awaiting_confirmation",
        "phase": DiscoveryPhase.MODULE_CONFIRMATION.value,
        "data": hook.discovery_metadata,
        "coverage": hook.discovery_coverage,
        "extracted_tags": hook.extracted_tags,
        "confirmation_message": confirmation_message,
        "workflow_preview": workflow_explanation,
    }


async def load_workflow_preview(db: AsyncSession, project_id: UUID) -> dict:
    hook = await get_or_create_hook(db, project_id)
    metadata = dict(hook.discovery_metadata or {})

    workflow_explanation = metadata.get("workflow_explanation")
    target_meta = metadata.get("target_structure") or {}
    seed_doctypes = target_meta.get("seed_doctypes", [])
    deferred_seeds = target_meta.get("deferred_doctypes", [])
    required_doctypes = target_meta.get("required_doctypes", [])

    # Fallback: read from project_target_structures if hooks JSON was not persisted
    if not workflow_explanation or not seed_doctypes:
        target_row = (
            await db.execute(
                select(ProjectTargetStructure).where(
                    ProjectTargetStructure.project_id == project_id
                )
            )
        ).scalar_one_or_none()
        if target_row:
            seed_doctypes = seed_doctypes or (target_row.seed_doctypes or [])
            deferred_seeds = deferred_seeds or (target_row.deferred_doctypes or [])
            required_doctypes = required_doctypes or (target_row.required_doctypes or [])
            if not workflow_explanation:
                workflow_explanation = await generate_workflow_explanation(
                    f3iche=metadata.get("f3iche_niche") or target_row.f3iche,
                    industry=metadata.get("industry", ""),
                    bottleneck=(metadata.get("mvp_focus") or {}).get("primary_bottleneck", ""),
                    target_structure={
                        "seed_doctypes": seed_doctypes,
                        "deferred_doctypes": deferred_seeds,
                        "required_doctypes": required_doctypes,
                        "setup_steps": target_row.setup_steps or [],
                    },
                    coverage=hook.discovery_coverage,
                    chat_transcript=transcript_text(normalize_messages(hook.chat_history)),
                    mvp_focus=metadata.get("mvp_focus"),
                    deferred_seeds=deferred_seeds,
                    dual_system_note=target_meta.get("dual_system_note", ""),
                    scoping_reasoning=target_meta.get("scoping_reasoning", ""),
                )
                metadata["workflow_explanation"] = workflow_explanation
                metadata["target_structure"] = metadata.get("target_structure") or {
                    "seed_doctypes": seed_doctypes,
                    "deferred_doctypes": deferred_seeds,
                    "required_doctypes": required_doctypes,
                }
                hook.discovery_metadata = metadata
                flag_modified(hook, "discovery_metadata")
                await db.commit()

    if not workflow_explanation:
        raise ValueError("Workflow preview not ready. Complete discovery first.")

    return {
        "phase": get_phase(metadata).value,
        "workflow_explanation": workflow_explanation,
        "seed_doctypes": seed_doctypes,
        "deferred_doctypes": deferred_seeds,
        "required_doctypes": required_doctypes,
        "discovery_metadata": metadata,
    }


async def confirm_discovery_modules(
    db: AsyncSession,
    project_id: UUID,
    *,
    confirmed_doctypes: list[str],
    added_doctypes: list[str] | None = None,
    removed_doctypes: list[str] | None = None,
    notes: str = "",
) -> dict:
    hook = await get_or_create_hook(db, project_id)
    metadata = dict(hook.discovery_metadata or {})

    if not metadata.get("target_structure"):
        raise ValueError("No target structure draft found. Complete discovery first.")

    project = await _get_project(db, project_id)

    target_payload = await generate_project_target_structure(
        db=db,
        project_id=project_id,
        company_slug=project.company_slug,
        user_confirmed_seeds=confirmed_doctypes,
        user_added_doctypes=added_doctypes or [],
    )

    metadata["user_module_adjustments"] = {
        "confirmed": confirmed_doctypes,
        "added": added_doctypes or [],
        "removed": removed_doctypes or [],
        "notes": notes,
    }
    metadata["target_structure"] = {
        "seed_doctypes": target_payload.get("seed_doctypes", []),
        "required_doctypes": target_payload.get("required_doctypes", []),
        "target_structure_id": target_payload.get("target_structure_id"),
        "mvp_boundary_id": target_payload.get("mvp_boundary_id"),
    }
    metadata["phase"] = DiscoveryPhase.FINALIZED.value
    metadata["target_confirmed_at"] = datetime.now(timezone.utc).isoformat()

    hook.discovery_metadata = metadata
    flag_modified(hook, "discovery_metadata")
    hook.discovery_status = "COMPLETE"
    await db.commit()

    return {
        "status": "finalized",
        "phase": DiscoveryPhase.FINALIZED.value,
        "data": metadata,
        "target": target_payload,
    }


def _format_f3iche(f3iche: str) -> str:
    mapping = {
        "manufacturing": "Manufacturing",
        "process_mfg_batch": "Process Manufacturing (Batch)",
        "discrete_mfg": "Discrete Manufacturing",
        "trading": "Trading & Distribution",
        "service": "Service",
        "retail": "Retail",
    }
    return mapping.get(f3iche, f3iche.replace("_", " ").title())
