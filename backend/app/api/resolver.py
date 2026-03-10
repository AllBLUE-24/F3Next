from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from shared.models.core import Project
from uuid import UUID
from pydantic import BaseModel
from shared.models.core import Client

router = APIRouter(prefix="/resolve", tags=["Core Resolver"])

class ProjectContext(BaseModel):
    project_id: UUID
    project_name: str
    status: str
    # Add other universal flags here (e.g., is_locked, tier)

@router.get("/slug/{slug_str}", response_model=ProjectContext)
async def resolve_project_slug(slug_str: str, db: AsyncSession = Depends(get_db)):
    """
    Universal endpoint: Converts a human-readable URL slug into a System UUID.
    Every frontend page hits this first.
    """
    # Query your Project table looking for the slug
    # Note: Ensure your Project model has a 'slug' column
    query = select(Project).where(Project.company_slug == slug_str)
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project slug not found")

    return {
        "project_id": project.id,
        "project_name": project.company_name,
        "status": project.status
    }

@router.get("/user/{firebase_uid}")
async def resolve_user_context(firebase_uid: str, db: AsyncSession = Depends(get_db)):
    """
    Given a Firebase UID, returns the user's slug and their company slug.
    Used for redirecting after login.
    """
    # 1. Fetch the Client (User)
    query = select(Client).where(Client.id == firebase_uid)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Fetch the Project associated with this Client
    # CORRECTED LOGIC: Search 'projects' table where client_id matches user.id
    project_query = select(Project).where(Project.client_id == user.id)
    
    p_result = await db.execute(project_query)
    project = p_result.scalar_one_or_none()
    
    if not project:
         # Handle case where user exists but has no project yet (maybe redirect to setup?)
         raise HTTPException(status_code=404, detail="Project context missing")

    return {
        "user_slug": user.user_slug,
        "company_slug": project.company_slug
    }