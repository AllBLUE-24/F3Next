from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from shared.models.core import Project
from uuid import UUID
from pydantic import BaseModel

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