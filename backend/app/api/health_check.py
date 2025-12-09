from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db

from app.models.core import Client, Project 
from app.models.hooks import Hook

from pydantic import BaseModel
from typing import Dict, Any
from agents.health_check.agent import run_health_check_agent 

router = APIRouter(prefix="/health_check", tags=["Health Check"])

class AnonymousSubmission(BaseModel):
    firebase_uid: str
    user_email: str
    full_name: str
    role: str
    company_name: str
    answers: Dict[str, Any]

@router.post("/submit")
async def submit_health_check(
    payload: AnonymousSubmission,
    db: AsyncSession = Depends(get_db),
):
    # 1. ENSURE CLIENT
    client_res = await db.execute(select(Client).where(Client.id == payload.firebase_uid))
    client = client_res.scalar_one_or_none()
    
    if not client:
        client = Client(
            id=payload.firebase_uid, 
            email=payload.user_email,
            full_name=payload.full_name,
            role=payload.role,
            company_name=payload.company_name,
            status="active"
        )
        db.add(client)
        await db.flush()
    else:
        # Update existing info
        if not client.company_name: client.company_name = payload.company_name
        if not client.full_name: client.full_name = payload.full_name

    # 2. ENSURE PROJECT
    proj_res = await db.execute(select(Project).where(Project.client_id == payload.firebase_uid))
    project = proj_res.scalar_one_or_none()

    if not project:
        project = Project(
            client_id=payload.firebase_uid, 
            company_name=payload.company_name,
            # We use the raw string to be 100% safe with Postgres Enums
            status=ProjectStatus.CREATED
        )
        db.add(project)
        await db.flush()

    # 3. SAVE HOOKS
    hook_res = await db.execute(select(Hook).where(Hook.project_id == project.id))
    existing_hook = hook_res.scalar_one_or_none()

    if existing_hook:
        existing_hook.answers_health_check = payload.answers
    else:
        new_hook = Hook(
            project_id=project.id,
            answers_health_check=payload.answers
        )
        db.add(new_hook)

    await db.commit()

    # 4. TRIGGER AGENT
    # The database part is DONE. Now we run the AI.
    print(f"🚀 Triggering Agent for Project {project.id}")
    report = await run_health_check_agent(payload.answers)

    # 🟢 CHANGE THE RETURN STATEMENT TO THIS:
    return {
        "status": "success",
        "project_id": str(project.id),
        "report": report,
        # 👇 THIS IS THE MISSING PIECE
        "user_meta": {
            "name": client.full_name,
            "company": client.company_name,
            "role": client.role
        }
    }