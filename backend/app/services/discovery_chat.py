"""
Synchronous discovery chat — DB orchestration (no Temporal).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from containers.discovery.chat_service import (
    MAX_USER_TURNS,
    _utc_now_iso,
    complete_discovery,
    count_user_turns,
    generate_chat_reply,
    normalize_messages,
    opening_messages,
)
from shared.models.hooks import Hook


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


async def load_session(db: AsyncSession, project_id: UUID) -> dict:
    hook = await get_or_create_hook(db, project_id)
    messages = _ensure_opening(hook)

    if normalize_messages(hook.chat_history) != messages:
        hook.chat_history = messages
        hook.last_bot_response = messages[-1]["content"] if messages else ""
        hook.discovery_status = hook.discovery_status or "ACTIVE"
        await db.commit()

    user_turns = count_user_turns(messages)
    is_complete = hook.discovery_status == "COMPLETE"

    return {
        "messages": messages,
        "status": hook.discovery_status or "ACTIVE",
        "is_complete": is_complete,
        "user_turns": user_turns,
        "ready_for_recommendation": user_turns >= 2 and not is_complete,
        "discovery_metadata": hook.discovery_metadata if is_complete else None,
        "coverage": hook.discovery_coverage,
    }


async def send_chat_message(db: AsyncSession, project_id: UUID, user_message: str) -> dict:
    hook = await get_or_create_hook(db, project_id)

    if hook.discovery_status == "COMPLETE":
        return {
            "reply": "Discovery is already complete. Head to your recommendation to continue.",
            "messages": normalize_messages(hook.chat_history),
            "status": "COMPLETE",
            "is_complete": True,
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
            "is_complete": False,
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
        "is_complete": False,
        "user_turns": user_turns,
        "ready_for_recommendation": user_turns >= 2,
    }


async def finalize_discovery(db: AsyncSession, project_id: UUID) -> dict:
    hook = await get_or_create_hook(db, project_id)

    if hook.discovery_status == "COMPLETE" and hook.discovery_metadata:
        return {
            "status": "ready",
            "data": hook.discovery_metadata,
            "coverage": hook.discovery_coverage,
            "extracted_tags": hook.extracted_tags or [],
        }

    messages = normalize_messages(hook.chat_history)
    if count_user_turns(messages) < 1:
        raise ValueError("Need at least one exchange before generating a recommendation.")

    result = await complete_discovery(messages)

    hook.chat_history = messages
    hook.discovery_coverage = result["coverage"]
    hook.extracted_tags = result["extracted_tags"]
    hook.discovery_metadata = result["discovery_metadata"]
    hook.discovery_status = "COMPLETE"
    hook.discovery_turn_count = count_user_turns(messages)
    hook.last_bot_response = messages[-1]["content"] if messages else hook.last_bot_response
    await db.commit()

    return {
        "status": "ready",
        "data": hook.discovery_metadata,
        "coverage": hook.discovery_coverage,
        "extracted_tags": hook.extracted_tags,
    }
