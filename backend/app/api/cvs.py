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

    try:
        from shared.cvs_metrics import CVS_FORCE_SYNC_TOTAL

        if CVS_FORCE_SYNC_TOTAL:
            CVS_FORCE_SYNC_TOTAL.labels(result="ok" if result.get("ok") else "fail").inc()
    except Exception:
        pass

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
      Temporal workflow logs the ContextEvent (single source of truth).
      If Temporal is unavailable, the endpoint returns an error and the ERP
      may retry; the recovery poller also catches stale unprocessed rows.
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

    # ── Step 4: Enqueue Temporal workflow (logs ContextEvent inside workflow) ─
    result = await launcher.trigger_webhook_sync(
        project_id      = str(project_id),
        company_slug    = company_slug,
        company_profile = company_profile,
        webhook_payload = payload_dict,
    )

    try:
        from shared.cvs_metrics import CVS_WEBHOOKS_TOTAL

        if CVS_WEBHOOKS_TOTAL:
            CVS_WEBHOOKS_TOTAL.labels(result="ok" if result.get("ok") else "fail").inc()
    except Exception:
        pass

    return {
        "ok":          result.get("ok"),
        "workflow_id": result.get("workflow_id"),
        "layers":      result.get("layers"),
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
    """Delegates to shared loader (workers + API use the same shape)."""
    from shared.cvs_profile import load_cvs_company_profile

    return await load_cvs_company_profile(project_id)
