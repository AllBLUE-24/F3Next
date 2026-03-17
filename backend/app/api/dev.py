"""Dev endpoints — test the app without Firebase auth."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.db import get_db
from shared.models.core import Client, Project, ProjectStatus
from shared.models.hooks import Hook
import uuid

router = APIRouter(prefix="/dev", tags=["Dev"])

COMPANY_SLUG = "test-company"
USER_SLUG = "test-user"


@router.post("/create-test-session")
async def create_test_session(db: AsyncSession = Depends(get_db)):
    """
    Creates a test user + project so you can test the app without Firebase.
    Returns the URL to open: /{company_slug}/{user_slug}/home
    Reuses existing test session if one already exists (avoids UNIQUE constraint on user_slug).
    """
    # 1. Check if test project already exists
    result = await db.execute(select(Project).where(Project.company_slug == COMPANY_SLUG))
    existing_project = result.scalar_one_or_none()
    if existing_project:
        client = (await db.execute(select(Client).where(Client.id == existing_project.client_id))).scalar_one()
        slug = client.user_slug or USER_SLUG
        return {
            "company_slug": COMPANY_SLUG,
            "user_slug": slug,
            "url": f"/{COMPANY_SLUG}/{slug}/home",
            "project_id": str(existing_project.id),
        }

    # 2. Check if test client already exists (handles race: another request may have created it)
    result = await db.execute(select(Client).where(Client.user_slug == USER_SLUG))
    existing_client = result.scalar_one_or_none()
    if existing_client:
        # Client exists but no project for test-company? Create project + hook
        proj_result = await db.execute(
            select(Project).where(
                Project.client_id == existing_client.id,
                Project.company_slug == COMPANY_SLUG,
            )
        )
        proj = proj_result.scalar_one_or_none()
        if not proj:
            proj = Project(
                client_id=existing_client.id,
                company_name="Test Company",
                company_slug=COMPANY_SLUG,
                status=ProjectStatus.CREATED,
            )
            db.add(proj)
            await db.flush()
            db.add(Hook(project_id=proj.id))
        await db.commit()
        return {
            "company_slug": COMPANY_SLUG,
            "user_slug": USER_SLUG,
            "url": f"/{COMPANY_SLUG}/{USER_SLUG}/home",
            "project_id": str(proj.id),
        }

    # 3. Create new test client + project + hook
    test_user_id = f"dev-test-{uuid.uuid4().hex[:8]}"
    try:
        client = Client(
            id=test_user_id,
            full_name="Test User",
            user_slug=USER_SLUG,
            company_name="Test Company",
        )
        db.add(client)
        project = Project(
            client_id=test_user_id,
            company_name="Test Company",
            company_slug=COMPANY_SLUG,
            status=ProjectStatus.CREATED,
        )
        db.add(project)
        await db.flush()
        db.add(Hook(project_id=project.id))
        await db.commit()
        return {
            "company_slug": COMPANY_SLUG,
            "user_slug": USER_SLUG,
            "url": f"/{COMPANY_SLUG}/{USER_SLUG}/home",
            "project_id": str(project.id),
        }
    except IntegrityError:
        await db.rollback()
        # Race: another request created the client. Fetch and return existing.
        result = await db.execute(select(Client).where(Client.user_slug == USER_SLUG))
        existing = result.scalar_one_or_none()
        if existing:
            proj_result = await db.execute(select(Project).where(Project.company_slug == COMPANY_SLUG))
            proj = proj_result.scalar_one_or_none()
            if proj:
                return {
                    "company_slug": COMPANY_SLUG,
                    "user_slug": USER_SLUG,
                    "url": f"/{COMPANY_SLUG}/{USER_SLUG}/home",
                    "project_id": str(proj.id),
                }
        raise
