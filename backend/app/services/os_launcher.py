"""
backend/app/services/os_launcher.py

Temporal client wrapper for the ERP-OS workflow.
This is the ONLY place in backend/ that touches Temporal directly.

Responsibilities:
  - Create and cache the Temporal client (one client per process lifetime)
  - Start ERPOSCommandWorkflow executions
  - Query workflow status via Temporal query handlers
  - Send signals (user_confirmation, user_answer)
  - Await the final workflow result
"""

from __future__ import annotations

import json
import logging
import uuid
import os
from dotenv import load_dotenv
load_dotenv()

from datetime import timedelta
from functools import lru_cache
from typing import Any, Optional

from temporalio.client import Client, WorkflowExecutionStatus, WorkflowHandle
from temporalio.common import RetryPolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from shared.models.command import (
    AnswerRequest,
    CommandDispatch,
    CommandRequest,
    CommandWorkflowInput,
    CommandWorkflowOutput, # 🔴 FIX: Added to prevent Temporal DataConverter errors!
    ConfirmationPreview,
    ConfirmationRequest,
    WorkflowResult,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────

TEMPORAL_HOST     = os.getenv("TEMPORAL_HOST")   # Override via env in production
OS_TASK_QUEUE     = "os-main-queue" # The first queue — workflow routes from here
WORKFLOW_TIMEOUT  = timedelta(hours=1) # Max time for a single command workflow

# ─── Temporal client (lazy singleton) ────────────────────────────────────────

_client: Optional[Client] = None


async def _get_client() -> Client:
    """Return a cached Temporal client. Created once per process."""
    global _client
    if _client is None:
        import os
        host = os.getenv("TEMPORAL_HOST", TEMPORAL_HOST)
        _client = await Client.connect(host)
        logger.info("Temporal client connected to %s", host)
    return _client


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_session_context(raw: Optional[str]) -> list[dict]:
    """Safely parse session_context JSON string → list of turn dicts."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _make_workflow_id() -> str:
    return f"os-cmd-{uuid.uuid4()}"


def _make_session_id() -> str:
    return f"sess-{uuid.uuid4().hex[:12]}"


# ─── 1. Dispatch — start the workflow ─────────────────────────────────────────

async def dispatch_os_command(req: CommandRequest) -> CommandDispatch:
    """
    Start ERPOSCommandWorkflow for the given NL command.
    Returns immediately with workflow_id — workflow runs async.
    """
    client      = await _get_client()
    workflow_id = _make_workflow_id()
    session_id  = req.session_id or _make_session_id()

    wf_input = CommandWorkflowInput(
        prompt          = req.prompt,
        project_id      = req.project_id,
        company_id      = req.company_id,
        user_id         = req.user_id,
        erp_type        = req.erp_type,
        session_id      = session_id,
        session_context = _parse_session_context(req.session_context),
        # 🟢 CRITICAL FIX: Pass the mode to the workflow! 
        # Without this, the workflow defaults to EXECUTE and fails on revenue queries.
        mode            = req.mode, 
    )

    # Import here to avoid circular import at module load
    from containers.os.os_workflow.workflow import ERPOSCommandWorkflow

    try:
        await client.start_workflow(
            ERPOSCommandWorkflow.run,
            wf_input,
            id                  = workflow_id,
            task_queue          = OS_TASK_QUEUE,
            execution_timeout   = WORKFLOW_TIMEOUT,
            retry_policy        = RetryPolicy(maximum_attempts=1),
        )
    except WorkflowAlreadyStartedError:
        logger.warning("Duplicate workflow ID attempted: %s", workflow_id)

    logger.info("Dispatched OS workflow %s with mode %s", workflow_id, req.mode)

    return CommandDispatch(
        status      = "dispatched",
        workflow_id = workflow_id,
        session_id  = session_id,
    )

# ─── 2. Query status ──────────────────────────────────────────────────────────

async def query_workflow_status(workflow_id: str) -> WorkflowStatus:
    """
    Query the live workflow for its current status.
    The workflow exposes a 'get_status' query handler that returns
    {"status": str, "confirmation_request": dict | None}.
    """
    client = await _get_client()
    handle: WorkflowHandle = client.get_workflow_handle(workflow_id)

    # Check if workflow exists / is running
    try:
        desc = await handle.describe()
    except Exception as e:
        raise LookupError(f"Workflow {workflow_id} not found: {e}") from e

    exec_status = desc.status

    # If terminated / timed out, return terminal status
    if exec_status == WorkflowExecutionStatus.TIMED_OUT:
        return WorkflowStatus(status="error")
    if exec_status == WorkflowExecutionStatus.TERMINATED:
        return WorkflowStatus(status="cancelled")
    if exec_status == WorkflowExecutionStatus.FAILED:
        return WorkflowStatus(status="error")

    # Query the workflow's internal state
    try:
        raw: dict[str, Any] = await handle.query("get_status")
    except Exception as e:
        logger.warning("Status query failed for %s: %s", workflow_id, e)
        return WorkflowStatus(status="polling")

    step   = raw.get("status", "polling")
    cr_raw = raw.get("confirmation_request")

    confirmation_request: Optional[ConfirmationRequest] = None

    if cr_raw and isinstance(cr_raw, dict):
        cr_type = cr_raw.get("type", "ambiguity")

        if cr_type == "ambiguity":
            confirmation_request = ConfirmationRequest(
                type     = "ambiguity",
                question = cr_raw.get("question", "Could you clarify?"),
                round    = cr_raw.get("round", 1),
            )
        elif cr_type == "confirmation":
            preview_raw = cr_raw.get("preview")
            preview     = None
            if preview_raw:
                preview = ConfirmationPreview(
                    action_summary   = preview_raw.get("action_summary", ""),
                    entities         = preview_raw.get("entities", []),
                    warnings         = preview_raw.get("warnings", []),
                    auto_corrections = preview_raw.get("auto_corrections", []),
                )
            confirmation_request = ConfirmationRequest(
                type       = "confirmation",
                risk_level = cr_raw.get("risk_level", "medium"),
                preview    = preview,
            )

    return WorkflowStatus(
        status               = step,
        confirmation_request = confirmation_request,
    )


# ─── 3. Get final result ──────────────────────────────────────────────────────

async def get_workflow_result(workflow_id: str) -> WorkflowResult:
    """
    Await the final result of a completed workflow.
    Should only be called after status == "done" or "error".
    """
    client = await _get_client()
    handle: WorkflowHandle = client.get_workflow_handle(workflow_id)

    try:
        output = await handle.result(
            follow_runs=True,
            rpc_timeout=timedelta(seconds=5),  # Don't block — caller should check status first
        )
        
        # Safely parse Temporal's output whether it's a dict or an object
        if isinstance(output, dict):
            return WorkflowResult(
                status   = output.get("status", "error"),
                response = output.get("response", "No response provided."),
                result   = output.get("result"),
                errors   = output.get("errors", [])
            )
        else:
            return WorkflowResult(
                status   = getattr(output, "status", "error"),
                response = getattr(output, "response", "No response provided."),
                result   = getattr(output, "result", None),
                errors   = getattr(output, "errors", [])
            )

    except TimeoutError:
        raise
    except Exception as e:
        logger.exception("Failed to get result for workflow %s: %s", workflow_id, e)
        
        # 🔴 ULTIMATE SAFETY NET: If handle.result() crashes (e.g. DataConverterError),
        # we bypass the crash by querying the live workflow to rescue the English translation!
        try:
            raw = await handle.query("get_status")
            if raw and raw.get("response"):
                return WorkflowResult(
                    status   = raw.get("status", "error"),
                    response = raw.get("response"), # The rescued English translation!
                    result   = None,
                    errors   = [{"message": "Recovered via workflow status query."}]
                )
        except Exception:
            pass

        return WorkflowResult(
            status   = "error",
            response = "An error occurred while retrieving the result.",
            errors   = [{"message": str(e)}],
        )


# ─── 4. Signal: user confirmation ─────────────────────────────────────────────

async def signal_confirmation(workflow_id: str, decision: str) -> None:
    client = await _get_client()
    handle: WorkflowHandle = client.get_workflow_handle(workflow_id)

    try:
        await handle.signal("user_confirmation", decision)
    except Exception as e:
        raise LookupError(f"Cannot signal workflow {workflow_id}: {e}") from e

    logger.info("Sent confirmation signal '%s' to workflow %s", decision, workflow_id)


# ─── 5. Signal: user answer to clarification ──────────────────────────────────

async def signal_user_answer(workflow_id: str, answer: str) -> None:
    client = await _get_client()
    handle: WorkflowHandle = client.get_workflow_handle(workflow_id)

    try:
        await handle.signal("user_answer", answer)
    except Exception as e:
        raise LookupError(f"Cannot signal workflow {workflow_id}: {e}") from e

    logger.info("Sent answer signal to workflow %s", workflow_id)


# ─── 6. List sessions ─────────────────────────────────────────────────────────

async def list_project_sessions(project_id: str, limit: int = 20) -> list[dict]:
    # Stub — replace with real DB logic later
    logger.debug("list_project_sessions stub called for %s", project_id)
    return []