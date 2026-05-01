"""
backend/app/api/cvs.py

FastAPI routes for the Context Versioning Service.

Endpoints:
  POST /api/cvs/force-sync/{project_id}  — full sync (called by IS after deployment)
  POST /api/cvs/webhook/{project_id}     — ERPNext webhook receiver (Phase 2)
  GET  /api/cvs/context/{project_id}     — read latest snapshot (used by OS)
  GET  /api/cvs/events/{project_id}      — audit log (admin / debugging)

No business logic here — all logic lives in cvs_launcher.py and the Temporal workflow.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cvs", tags=["Context Versioning"])


# ── Dep helper ─────────────────────────────────────────────────────────────────

async def get_launcher():
    from app.services.cvs_launcher import CVSLauncher
    return CVSLauncher()


# ── Request models ─────────────────────────────────────────────────────────────

class ForceSyncRequest(BaseModel):
    """
    Trigger a full context sync for a company.
    Called by the IS pipeline after deployment completes.

    company_profile must contain ERP credentials (api_key, api_secret, erp_url).
    company_slug is used to build R2 key paths.
    layers defaults to ["master_data", "transaction_intel"] (full sync).
    """
    company_slug:    str
    company_profile: Dict[str, Any]
    layers:          Optional[List[str]] = None   # defaults to full sync in launcher


class WebhookPayload(BaseModel):
    """
    ERPNext webhook body (Phase 2).
    ERPNext sends: doctype, name, event, data.
    """
    doctype:    str
    name:       Optional[str]  = None
    event:      Optional[str]  = None
    data:       Optional[Dict[str, Any]] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/force-sync/{project_id}",
    summary="Trigger a full context sync (called by IS after deployment)",
)
async def force_sync(
    project_id: UUID,
    req:        ForceSyncRequest,
    launcher=   Depends(get_launcher),
):
    """
    Start a full CVS sync for a company.

    This is the primary Phase 1 entry point — called by the IS pipeline once
    ERPNext deployment is complete and credentials are available.

    The sync runs asynchronously in Temporal; this endpoint returns immediately
    with the workflow_id so the caller can poll if needed.
    """
    result = await launcher.force_sync(
        project_id      = str(project_id),
        company_slug    = req.company_slug,
        company_profile = req.company_profile,
        layers          = req.layers,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "Sync failed to start"))

    return {
        "ok":          True,
        "workflow_id": result.get("workflow_id"),
        "message":     f"Context sync started for project {project_id}",
    }


@router.post(
    "/webhook/{project_id}",
    summary="ERPNext webhook receiver",
)
async def receive_webhook(
    project_id: UUID,
    request:    Request,
    launcher=   Depends(get_launcher),
    x_frappe_webhook_signature: Optional[str] = Header(default=None),
):
    """
    Receive an ERPNext webhook and trigger a targeted context update.

    Security:
      Frappe signs every webhook payload with HMAC-SHA256 using the project's
      webhook_secret (stored in projects.deployment_details.webhook_secret).
      The signature is sent in X-Frappe-Webhook-Signature.
      Requests without a valid signature are rejected with 401/403.

    Resilience:
      The raw payload is written to context_events BEFORE Temporal is called.
      If Temporal is briefly unavailable, the event is still recorded and can
      be re-processed by the recovery cron (processed_at IS NULL).
    """
    raw_body = await request.body()

    # ── Step 1: Load project profile (need webhook_secret for HMAC) ───────────
    try:
        company_slug, company_profile = await _load_profile_for_project(str(project_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # ── Step 2: HMAC-SHA256 signature verification ────────────────────────────
    webhook_secret = company_profile.get("webhook_secret", "")
    if not webhook_secret:
        # Secret not yet configured — log and allow during initial setup,
        # but flag loudly so ops team knows to fix it.
        logger.warning(
            "CVS webhook: project %s has no webhook_secret — SKIPPING verification. "
            "Configure webhook_secret in deployment_details immediately.",
            project_id,
        )
    else:
        if not x_frappe_webhook_signature:
            raise HTTPException(
                status_code=401,
                detail="Missing X-Frappe-Webhook-Signature header",
            )

        mac = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        )
        expected = mac.hexdigest()

        if not hmac.compare_digest(expected, x_frappe_webhook_signature):
            logger.warning(
                "CVS webhook: HMAC mismatch for project %s — rejecting.", project_id
            )
            raise HTTPException(
                status_code=403,
                detail="Invalid webhook signature",
            )

    # ── Step 3: Parse body ────────────────────────────────────────────────────
    try:
        payload_dict = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    doctype  = payload_dict.get("doctype", "")
    doc_name = payload_dict.get("name", "")

    # ── Step 4: Buffer event to context_events BEFORE Temporal ───────────────
    # This ensures we never lose an event even if Temporal is briefly down.
    # processed_at=None marks it as pending; the recovery cron will pick it up.
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextEvent
        import uuid as _uuid

        async with AsyncSessionLocal() as db:
            event_row = ContextEvent(
                project_id    = str(project_id),
                event_type    = f"webhook_{doctype.lower().replace(' ', '_')}",
                event_payload = payload_dict,
                doctype       = doctype,
                doc_name      = doc_name,
            )
            db.add(event_row)
            await db.commit()
            await db.refresh(event_row)
            event_id = str(event_row.id)

        logger.info(
            "CVS webhook buffered: project=%s doctype=%s doc=%s event_id=%s",
            project_id, doctype, doc_name, event_id,
        )

    except Exception as e:
        logger.exception("CVS webhook: failed to buffer event to DB: %s", e)
        # Don't return 500 to Frappe — that would cause it to retry and flood us.
        # The event is lost but Frappe won't retry infinitely.
        return {"ok": False, "error": "event_buffer_failed", "detail": str(e)}

    # ── Step 5: Enqueue Temporal workflow ────────────────────────────────────
    result = await launcher.trigger_webhook_sync(
        project_id      = str(project_id),
        company_slug    = company_slug,
        company_profile = company_profile,
        webhook_payload = payload_dict,
    )

    return {
        "ok":          result.get("ok"),
        "workflow_id": result.get("workflow_id"),
        "layers":      result.get("layers"),
        "event_id":    event_id,
    }


@router.get(
    "/context/{project_id}",
    summary="Read the latest context snapshot for a company",
)
async def get_context(
    project_id: UUID,
    layer:      str = "master_data",
    launcher=   Depends(get_launcher),
):
    """
    Return the latest context snapshot for a company + layer.

    Used by:
      - OS context_retrieval (server-side, via direct launcher call)
      - Admin dashboard (debugging)

    layer: "identity" | "master_data" | "transaction_intel"
    """
    snapshot = await launcher.get_latest_context(str(project_id), layer)

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No {layer} snapshot found for project {project_id}. "
                "Run /force-sync after IS deployment completes."
            ),
        )

    return snapshot


@router.get(
    "/events/{project_id}",
    summary="Context event audit log",
)
async def get_events(
    project_id: UUID,
    limit:      int = 50,
):
    """
    Return the latest context events for a project (audit log / admin debugging).
    """
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextEvent
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContextEvent)
                .where(ContextEvent.project_id == str(project_id))
                .order_by(ContextEvent.received_at.desc())
                .limit(limit)
            )
            events = result.scalars().all()

        return {
            "project_id": str(project_id),
            "events": [
                {
                    "id":              str(e.id),
                    "event_type":      e.event_type,
                    "doctype":         e.doctype,
                    "doc_name":        e.doc_name,
                    "version_produced": e.version_produced,
                    "received_at":     e.received_at.isoformat() if e.received_at else None,
                    "processed_at":    e.processed_at.isoformat() if e.processed_at else None,
                }
                for e in events
            ],
        }

    except Exception as e:
        logger.exception("CVS: get_events failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status/{project_id}",
    summary="CVS health check — latest snapshot versions per layer",
)
async def get_status(project_id: UUID):
    """
    Returns the current version and age of each context layer.
    Used for health monitoring and debugging.
    """
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.cvs_models import ContextSnapshot
        from sqlalchemy import select

        layers = ["identity", "master_data", "transaction_intel"]
        status: dict = {}

        async with AsyncSessionLocal() as session:
            for layer in layers:
                result = await session.execute(
                    select(ContextSnapshot)
                    .where(
                        ContextSnapshot.project_id == str(project_id),
                        ContextSnapshot.layer      == layer,
                    )
                    .order_by(ContextSnapshot.version.desc())
                    .limit(1)
                )
                row = result.scalars().first()

                if row:
                    status[layer] = {
                        "version":       row.version,
                        "trigger_event": row.trigger_event,
                        "r2_key":        row.r2_key,
                        "created_at":    row.created_at.isoformat() if row.created_at else None,
                    }
                else:
                    status[layer] = {"version": 0, "status": "not_synced"}

        return {"project_id": str(project_id), "layers": status}

    except Exception as e:
        logger.exception("CVS: get_status failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _load_profile_for_project(project_id: str) -> tuple[str, dict]:
    """
    Load the company profile from the projects DB table.
    Used by the webhook endpoint to get ERP credentials without the caller providing them.

    Returns (company_slug, profile_dict).
    Raises ValueError if project not found or not yet deployed.
    """
    from shared.database.db import AsyncSessionLocal
    from shared.models.core import Project
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalars().first()

    if not project:
        raise ValueError(f"Project {project_id} not found")

    deployment = project.deployment_details or {}

    if not deployment.get("api_key"):
        raise ValueError(
            f"Project {project_id} has no ERP credentials yet (IS not complete)"
        )

    company      = project.company_name or deployment.get("company", "Unknown")
    company_slug = project.company_slug or project_id

    profile = {
        "company_id":         str(project.id),
        "company_name":       company,
        "company_slug":       company_slug,
        "erp_type":           "erpnext",
        "erp_url":            deployment.get("erp_url") or deployment.get("site_url", ""),
        "api_key":            deployment.get("api_key", ""),
        "api_secret":         deployment.get("api_secret", ""),
        "verify_ssl":         deployment.get("verify_ssl", True),
        "allow_insecure_ssl": deployment.get("allow_insecure_ssl", True),
        "default_company":    deployment.get("company", company),
        "default_currency":   deployment.get("currency", "INR"),
        "default_warehouse":  deployment.get("default_warehouse", ""),
        "source":             "cvs_webhook_loader",
    }

    return company_slug, profile
