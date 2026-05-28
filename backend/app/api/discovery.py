from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.discovery_chat import finalize_discovery, load_session, send_chat_message
from shared.database.db import get_shared_db
from shared.models.core import Project
from shared.models.hooks import Hook

router = APIRouter(prefix="/discovery", tags=["Discovery"])


class DiscoveryRequest(BaseModel):
    project_id: UUID
    message: str
    step: int = 1  # legacy — ignored


class CompleteRequest(BaseModel):
    project_id: UUID


@router.get("/session/{project_id}")
async def get_discovery_session(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """Load chat history and session state (ChatGPT-style — no polling needed)."""
    res = await db.execute(select(Project).where(Project.id == project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        return await load_session(db, project_id)
    except Exception as e:
        print(f"❌ Discovery session error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_discovery(request: DiscoveryRequest, db: AsyncSession = Depends(get_shared_db)):
    """
    Synchronous discovery chat — send a message, get Adi's reply immediately.
    Stores full history in hooks.chat_history (JSONB).
    """
    res = await db.execute(select(Project).where(Project.id == request.project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = await send_chat_message(db, request.project_id, request.message)
        return result
    except Exception as e:
        print(f"❌ Discovery chat error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete")
async def complete_discovery(request: CompleteRequest, db: AsyncSession = Depends(get_shared_db)):
    """
    End discovery — extract signals from full transcript + generate ERP recommendation.
    Writes discovery_metadata for IS handoff.
    """
    res = await db.execute(select(Project).where(Project.id == request.project_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        return await finalize_discovery(db, request.project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Discovery complete error: {e!r}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}")
async def get_discovery_status(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """Backward-compatible status endpoint — delegates to session loader."""
    try:
        session = await load_session(db, project_id)
        return {
            "bot_response": (
                session["messages"][-1]["content"]
                if session.get("messages")
                else ""
            ),
            "messages": session.get("messages", []),
            "extracted_tags": [],
            "step": 1,
            "turn_count": session.get("user_turns", 0),
            "status": session.get("status"),
            "is_complete": session.get("is_complete", False),
            "coverage": session.get("coverage") or {
                "industry": {"status": None, "value": None},
                "strategy": {"status": None, "value": None},
                "scale": {"status": None, "value": None},
                "legacy_system": {"status": None, "value": None},
                "pain_point": {"status": None, "value": None},
            },
            "ready_for_recommendation": session.get("ready_for_recommendation", False),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/recommendation")
async def get_recommendation_status(project_id: UUID, db: AsyncSession = Depends(get_shared_db)):
    """Poll final ERP recommendation (ready immediately after POST /complete)."""
    try:
        query = select(Hook).where(Hook.project_id == project_id)
        result = await db.execute(query)
        hook = result.scalar_one_or_none()

        if not hook:
            raise HTTPException(status_code=404, detail="Project context not found")

        if not hook.discovery_metadata:
            return {"status": "processing"}

        return {
            "status": "ready",
            "data": hook.discovery_metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
