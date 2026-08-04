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

# Workflow clarification `type` values that should surface as ClarificationBlock payloads.
_CLARIFICATION_TYPES = frozenset(
    {"ambiguity", "business_clarification", "semantic_validation_fix"}
)

# ─── Configuration ────────────────────────────────────────────────────────────

TEMPORAL_HOST     = os.getenv("TEMPORAL_HOST")   # Override via env in production
OS_TASK_QUEUE     = "os-main-queue" # The first queue — workflow routes from here
WORKFLOW_TIMEOUT  = timedelta(hours=1) # Max time for a single command workflow

# ─── Temporal client (lazy singleton) ────────────────────────────────────────

_client: Optional[Client] = None


def _coerce_round(value: Any, *, default: int = 1) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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

def _is_uuid(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


async def _normalize_project_identifiers(
    project_id: str,
    company_id: str,
) -> tuple[str, str]:
    """
    Normalize incoming identifiers into:
      - project_id: UUID string (canonical internal identifier)
      - company_id: company_slug (human-friendly / legacy identifier)

    Accepts either field containing either UUID or slug, for backward compatibility.
    """
    raw_project_id = (project_id or "").strip()
    raw_company_id = (company_id or "").strip()

    uuid_str: Optional[str] = None
    slug: Optional[str] = None

    # Prefer explicit UUIDs if provided
    if _is_uuid(raw_project_id):
        uuid_str = str(uuid.UUID(raw_project_id))
    elif _is_uuid(raw_company_id):
        uuid_str = str(uuid.UUID(raw_company_id))

    # Prefer explicit slugs if provided
    if raw_company_id and not _is_uuid(raw_company_id):
        slug = raw_company_id
    elif raw_project_id and not _is_uuid(raw_project_id):
        slug = raw_project_id

    # Resolve missing side from DB (best effort, never hard-fail dispatch)
    if uuid_str is None or slug is None:
        try:
            from shared.database.db import AsyncSessionLocal
            from sqlalchemy import text

            params: dict[str, Any] = {}
            where = []

            if uuid_str is not None:
                params["pid"] = uuid.UUID(uuid_str)
                where.append("id = :pid")
            if slug is not None:
                params["slug"] = slug
                where.append("company_slug = :slug")

            if where:
                query = text(
                    f"""
                    SELECT id, company_slug
                    FROM projects
                    WHERE {" OR ".join(where)}
                    LIMIT 1
                    """
                )
                async with AsyncSessionLocal() as session:
                    res = await session.execute(query, params)
                    row = res.mappings().first()

                if row:
                    if uuid_str is None and row.get("id"):
                        uuid_str = str(row["id"])
                    if slug is None and row.get("company_slug"):
                        slug = str(row["company_slug"])
        except Exception as e:
            logger.warning(
                "OS dispatch: failed to normalize identifiers project_id=%s company_id=%s: %s",
                raw_project_id,
                raw_company_id,
                e,
            )

    # Last resort: keep inputs stable
    if uuid_str is None:
        uuid_str = raw_project_id or raw_company_id
    if slug is None:
        slug = raw_company_id or raw_project_id

    return uuid_str, slug


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

    project_uuid, company_slug = await _normalize_project_identifiers(
        project_id=req.project_id,
        company_id=req.company_id,
    )

    wf_input = CommandWorkflowInput(
        prompt          = req.prompt,
        project_id      = project_uuid,
        company_id      = company_slug,
        user_id         = req.user_id,
        erp_type        = req.erp_type,
        session_id      = session_id,
        session_context = _parse_session_context(req.session_context),
        mode            = req.mode,
        seed_context    = req.seed_context,
        origin_notification_id = req.origin_notification_id,
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
        cr_type = str(cr_raw.get("type", "ambiguity"))

        if cr_type in _CLARIFICATION_TYPES:
            cands_raw = cr_raw.get("candidates")
            candidates: list[str] | None = None
            if isinstance(cands_raw, list):
                candidates = [str(c) for c in cands_raw if c]
            confirmation_request = ConfirmationRequest(
                type     = "ambiguity",
                question = cr_raw.get("question", "Could you clarify?"),
                round    = _coerce_round(cr_raw.get("round"), default=1),
                field    = cr_raw.get("field"),
                candidates = candidates,
                severity = cr_raw.get("severity"),
            )
        elif cr_type == "semantic_validation_confirm":
            warnings_raw = cr_raw.get("warnings") or []
            norm_warnings: list[dict[str, str]] = []
            if isinstance(warnings_raw, list):
                for w in warnings_raw:
                    if isinstance(w, dict):
                        norm_warnings.append(
                            {
                                "field": str(w.get("field", "") or ""),
                                "message": str(w.get("message", "") or w),
                            }
                        )
                    else:
                        norm_warnings.append({"field": "", "message": str(w)})
            q = str(
                cr_raw.get("question")
                or "I found potential business issues. Proceed, or cancel to revise?"
            )
            confirmation_request = ConfirmationRequest(
                type       = "confirmation",
                risk_level = "medium",
                preview    = ConfirmationPreview(
                    action_summary   = q,
                    entities         = [],
                    warnings         = norm_warnings,
                    auto_corrections = [],
                ),
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