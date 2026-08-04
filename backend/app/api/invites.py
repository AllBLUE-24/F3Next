"""Team invite API — create, validate, accept, list, revoke."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.db import get_shared_db
from shared.erp_policies.departments import Department, DEPARTMENT_LABELS
from shared.models.core import Client, Project, ProjectMember, TeamInvite

router = APIRouter(prefix="/invites", tags=["Invites"])

INVITE_TTL_DAYS = 14


def _generate_code() -> str:
    return secrets.token_urlsafe(12)


class CreateInviteRequest(BaseModel):
    user_id: str
    company_slug: str
    email: Optional[str] = None
    department: Optional[str] = None


class AcceptInviteRequest(BaseModel):
    invite_code: str
    user_id: str
    full_name: str
    user_slug: str
    role: str
    department: Optional[str] = None


class UpdateMemberDepartmentRequest(BaseModel):
    user_id: str
    company_slug: str
    member_client_id: str
    department: Optional[str] = None


class RevokeInviteRequest(BaseModel):
    user_id: str
    invite_id: UUID


async def _project_for_slug(db: AsyncSession, company_slug: str) -> Project:
    result = await db.execute(select(Project).where(Project.company_slug == company_slug))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Company workspace not found")
    return project


async def _assert_admin(db: AsyncSession, user_id: str, project: Project) -> None:
    if project.client_id == user_id:
        return
    raise HTTPException(status_code=403, detail="Only the workspace owner can manage invites")


@router.post("/create")
async def create_invite(body: CreateInviteRequest, db: AsyncSession = Depends(get_shared_db)):
    project = await _project_for_slug(db, body.company_slug)
    await _assert_admin(db, body.user_id, project)

    code = _generate_code()
    dept = Department.normalize(body.department) if body.department else None
    if body.department and not dept:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid department. Choose one of: {', '.join(Department.values())}",
        )

    invite = TeamInvite(
        project_id=project.id,
        invite_code=code,
        email=body.email,
        department=dept,
        invited_by=body.user_id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return {
        "invite_id": str(invite.id),
        "invite_code": invite.invite_code,
        "invite_url": f"/{body.company_slug}/invite/{invite.invite_code}",
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
    }


@router.get("/validate")
async def validate_invite(
    code: str = Query(...),
    slug: str = Query(...),
    db: AsyncSession = Depends(get_shared_db),
):
    result = await db.execute(
        select(TeamInvite, Project)
        .join(Project, TeamInvite.project_id == Project.id)
        .where(TeamInvite.invite_code == code, Project.company_slug == slug)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Invite not found")

    invite, project = row
    if invite.status == "revoked":
        raise HTTPException(status_code=410, detail="This invite has been revoked")
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This invite has expired")

    return {
        "company_name": project.company_name,
        "company_slug": project.company_slug,
        "invite_code": invite.invite_code,
        "status": invite.status,
        "department": invite.department,
        "department_label": DEPARTMENT_LABELS.get(invite.department or "", invite.department),
    }


@router.post("/accept")
async def accept_invite(body: AcceptInviteRequest, db: AsyncSession = Depends(get_shared_db)):
    result = await db.execute(
        select(TeamInvite, Project).join(Project, TeamInvite.project_id == Project.id).where(
            TeamInvite.invite_code == body.invite_code
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Invite not found")

    invite, project = row
    if invite.status == "revoked":
        raise HTTPException(status_code=410, detail="This invite has been revoked")
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This invite has expired")

    if project.client_id == body.user_id:
        raise HTTPException(status_code=400, detail="You already own this workspace")

    member_check = await db.execute(
        select(ProjectMember).where(ProjectMember.client_id == body.user_id)
    )
    if member_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You are already a member of a workspace")

    client_result = await db.execute(select(Client).where(Client.id == body.user_id))
    user = client_result.scalar_one_or_none()
    if not user:
        user = Client(id=body.user_id)
        db.add(user)

    user.full_name = body.full_name.strip()
    user.user_slug = body.user_slug.strip()
    user.role = body.role.strip()
    user.company_name = project.company_name

    member_department = Department.normalize(body.department) if body.department else invite.department
    if body.department and not member_department:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid department. Choose one of: {', '.join(Department.values())}",
        )

    db.add(
        ProjectMember(
            project_id=project.id,
            client_id=body.user_id,
            role=body.role.strip(),
            department=member_department,
        )
    )

    if invite.email:
        invite.status = "accepted"

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not join workspace: {exc}") from exc

    return {
        "status": "success",
        "company_slug": project.company_slug,
        "user_slug": body.user_slug,
        "redirect_url": f"/{project.company_slug}/{body.user_slug}/home",
        "department": member_department,
    }


@router.get("/members")
async def list_members(
    company_slug: str = Query(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_shared_db),
):
    """List workspace members with department assignments (admin only)."""
    project = await _project_for_slug(db, company_slug)
    await _assert_admin(db, user_id, project)

    result = await db.execute(
        select(ProjectMember, Client)
        .join(Client, ProjectMember.client_id == Client.id)
        .where(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.joined_at.asc())
    )
    rows = result.all()

    return {
        "members": [
            {
                "client_id": member.client_id,
                "full_name": client.full_name,
                "email": client.email,
                "role": member.role,
                "department": member.department,
                "department_label": DEPARTMENT_LABELS.get(member.department or "", member.department),
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "is_owner": member.client_id == project.client_id,
            }
            for member, client in rows
        ]
    }


@router.post("/members/department")
async def update_member_department(
    body: UpdateMemberDepartmentRequest,
    db: AsyncSession = Depends(get_shared_db),
):
    project = await _project_for_slug(db, body.company_slug)
    await _assert_admin(db, body.user_id, project)

    if body.member_client_id == project.client_id:
        raise HTTPException(status_code=400, detail="Cannot change the workspace owner's department here")

    dept = Department.normalize(body.department) if body.department else None
    if body.department and not dept:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid department. Choose one of: {', '.join(Department.values())}",
        )

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.client_id == body.member_client_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.department = dept
    await db.commit()

    return {
        "status": "updated",
        "client_id": body.member_client_id,
        "department": dept,
    }


@router.get("/list")
async def list_invites(
    company_slug: str = Query(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_shared_db),
):
    project = await _project_for_slug(db, company_slug)
    await _assert_admin(db, user_id, project)

    result = await db.execute(
        select(TeamInvite)
        .where(TeamInvite.project_id == project.id, TeamInvite.status != "revoked")
        .order_by(TeamInvite.created_at.desc())
    )
    invites = result.scalars().all()

    return {
        "invites": [
            {
                "id": str(inv.id),
                "invite_code": inv.invite_code,
                "invite_url": f"/{company_slug}/invite/{inv.invite_code}",
                "email": inv.email,
                "department": inv.department,
                "department_label": DEPARTMENT_LABELS.get(inv.department or "", inv.department),
                "status": inv.status,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            }
            for inv in invites
        ]
    }


@router.post("/revoke")
async def revoke_invite(body: RevokeInviteRequest, db: AsyncSession = Depends(get_shared_db)):
    result = await db.execute(select(TeamInvite).where(TeamInvite.id == body.invite_id))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    project_result = await db.execute(select(Project).where(Project.id == invite.project_id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _assert_admin(db, body.user_id, project)
    invite.status = "revoked"
    await db.commit()
    return {"status": "revoked", "invite_id": str(invite.id)}
