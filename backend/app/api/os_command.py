"""
backend/app/api/os_command.py

FastAPI router for the ERP Operating System.
Mounts at: /api/os

All routes are thin — they validate the request and delegate entirely
to os_launcher.py which owns the Temporal client and workflow logic.

Register in backend/app/main.py:
    from backend.app.api.os_command import router as os_router
    app.include_router(os_router)
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, status

from backend.app.services.os_launcher import (
    dispatch_os_command,
    query_workflow_status,
    get_workflow_result,
    signal_confirmation,
    signal_user_answer,
    list_project_sessions,
)
from shared.models.command import (
    CommandRequest,
    CommandDispatch,
    ConfirmRequest,
    AnswerRequest,
    WorkflowStatus,
    WorkflowResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/os", tags=["Operating System"])


# ─── 0. Health Check ──────────────────────────────────────────────────────────

@router.get(
    "/ping",
    summary="Health check for OS router",
    description="Hit this endpoint (GET /api/os/ping) to verify the router is successfully mounted in main.py",
)
async def ping_os() -> dict:
    return {"status": "ok", "message": "ERP-OS Router is alive and mounted!"}


# ─── 1. Submit a new NL command ───────────────────────────────────────────────

@router.post(
    "/command",
    response_model=CommandDispatch,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a natural language ERP command",
    description=(
        "Accepts a natural language prompt, launches the ERP-OS Temporal workflow, "
        "and immediately returns a workflow_id for status polling. "
        "The command executes asynchronously through the 8-agent pipeline."
    ),
)
async def submit_command(body: CommandRequest) -> CommandDispatch:
    try:
        return await dispatch_os_command(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to dispatch OS command: %s", e)
        raise HTTPException(status_code=500, detail="Failed to launch command workflow") from e


# ─── 2. Poll workflow status ───────────────────────────────────────────────────

@router.get(
    "/status/{workflow_id}",
    response_model=WorkflowStatus,
    summary="Poll current pipeline status",
    description=(
        "Polled by the frontend every 1.5 seconds. Returns the current agent step "
        "and, if the workflow is paused, a confirmation_request object for the UI "
        "to render either a ClarificationBlock or ConfirmationBlock."
    ),
)
async def get_status(
    workflow_id: str = Path(..., description="Workflow ID from /command response"),
) -> WorkflowStatus:
    try:
        return await query_workflow_status(workflow_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Status query failed for %s: %s", workflow_id, e)
        raise HTTPException(status_code=500, detail="Failed to query workflow status") from e


# ─── 3. Get final result ───────────────────────────────────────────────────────

@router.get(
    "/result/{workflow_id}",
    response_model=WorkflowResult,
    summary="Get the final formatted result",
    description=(
        "Called by the frontend only after status === 'done'. "
        "Returns the human-readable Result Formatter output and raw ERP response."
    ),
)
async def get_result(
    workflow_id: str = Path(..., description="Workflow ID from /command response"),
) -> WorkflowResult:
    try:
        return await get_workflow_result(workflow_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail="Workflow result not yet available") from e
    except Exception as e:
        logger.exception("Result fetch failed for %s: %s", workflow_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow result") from e


# ─── 4. Send confirmation signal ──────────────────────────────────────────────

@router.post(
    "/confirm/{workflow_id}",
    status_code=status.HTTP_200_OK,
    summary="Send user confirmation or cancellation",
    description=(
        "Sent when the user clicks Confirm or Cancel in the ConfirmationBlock UI. "
        "Signals the paused Temporal workflow to proceed or abort."
    ),
)
async def confirm_command(
    body: ConfirmRequest,
    workflow_id: str = Path(..., description="Workflow ID to signal"),
) -> dict:
    try:
        await signal_confirmation(workflow_id, body.decision)
        return {"detail": "Confirmation signal sent"}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Confirmation signal failed for %s: %s", workflow_id, e)
        raise HTTPException(status_code=500, detail="Failed to send confirmation") from e


# ─── 5. Send clarification answer ─────────────────────────────────────────────

@router.post(
    "/answer/{workflow_id}",
    status_code=status.HTTP_200_OK,
    summary="Send answer to a clarification question",
    description=(
        "Sent when the user submits an answer in the ClarificationBlock UI. "
        "Signals the paused Temporal workflow to retry intent extraction with the answer."
    ),
)
async def send_answer(
    body: AnswerRequest,
    workflow_id: str = Path(..., description="Workflow ID to signal"),
) -> dict:
    try:
        await signal_user_answer(workflow_id, body.answer)
        return {"detail": "Answer signal sent"}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Answer signal failed for %s: %s", workflow_id, e)
        raise HTTPException(status_code=500, detail="Failed to send answer") from e


# ─── 6. List sessions for a project ───────────────────────────────────────────

@router.get(
    "/sessions/{project_id}",
    summary="List command sessions for a project",
    description="Returns recent OS command sessions for the history page.",
)
async def get_sessions(
    project_id: str = Path(..., description="Project / company ID"),
    limit: Optional[int] = Query(default=20, ge=1, le=100),
) -> dict:
    try:
        sessions = await list_project_sessions(project_id, limit=limit or 20)
        return {"sessions": sessions}
    except Exception as e:
        logger.exception("Session list failed for %s: %s", project_id, e)
        raise HTTPException(status_code=500, detail="Failed to list sessions") from e