"""
containers/OS/execution_agent/activities.py

Temporal activity for the Execution Agent.
Registered on: os-main-queue (via os_worker.py)

Activity name: "execute_command"  ← must match workflow.py call exactly

Input:
  payload_bundle dict  — from Payload Generator
    {
      "steps": [
        {
          "step_number": 1,
          "action":      "create",
          "doctype":     "Sales Order",
          "endpoint":    "/api/resource/Sales%20Order",
          "http_method": "POST",
          "payload":     {...},
        }
      ]
    }
  plan dict    — from Command Planner (risk_level, rollback_strategy, etc.)
  context dict — from Context Retrieval (has erp_credentials)

Output:
  {
    "success":          bool,
    "result":           dict,   ← first step result (or last successful)
    "steps_results":    [...],  ← per-step detail
    "execution_time_ms": int,
    "error":            dict | None,
  }

FAIL BEHAVIOUR:
  - HTTP 4xx (bad request, auth, not found): raise → workflow marks error
  - HTTP 5xx / network timeout: retry via _RETRY_3 in workflow.py (max 3x)
  - Crash in activity code: fail-open, return success=False with error detail

No LLM. Timeout: 60 seconds (set in workflow.py).
"""

from __future__ import annotations

import logging
import time
from urllib.parse import quote

import aiohttp
from temporalio import activity

logger = logging.getLogger(__name__)

# ── HTTP status codes that should NOT be retried ──────────────────────────────
_NO_RETRY_STATUSES = {400, 401, 403, 404, 409, 417, 422}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_headers(api_key: str, api_secret: str) -> dict:
    return {
        "Authorization": f"token {api_key}:{api_secret}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def _erp_url(base: str, endpoint: str) -> str:
    """Safely join base URL and endpoint."""
    base    = base.rstrip("/")
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    return f"{base}{endpoint}"


def _parse_erp_error(status: int, body: dict) -> str:
    """Extract a human-readable error from ERPNext response."""
    exc = body.get("exception", "")
    msg = body.get("message", "")
    exc_type = body.get("exc_type", "")

    if exc_type:
        return f"{exc_type}: {exc or msg}"
    if exc:
        return exc.split("\n")[-1].strip() or exc
    return msg or f"ERPNext returned HTTP {status}"


# ── Core HTTP caller (reusable per step) ──────────────────────────────────────

async def _call_erpnext(
    session:    aiohttp.ClientSession,
    method:     str,
    url:        str,
    headers:    dict,
    payload:    dict,
    step_num:   int,
) -> dict:
    """
    Fire one HTTP request to ERPNext and return a normalised result dict.
    Raises ValueError for non-retryable 4xx errors.
    Raises RuntimeError for 5xx errors (will be retried by Temporal).
    """
    activity.heartbeat(f"Calling ERPNext: {method} {url} (step {step_num})")

    method = method.upper()

    async with getattr(session, method.lower())(
        url,
        json=payload if method in ("POST", "PUT", "PATCH") else None,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=45),
    ) as resp:
        status = resp.status
        try:
            body = await resp.json(content_type=None)
        except Exception:
            body = {"message": await resp.text()}

    if status in (200, 201):
        data = body.get("data", body)
        activity.logger.info(
            "  ✅ step %d: %s %s → %s (doc: %s)",
            step_num, method, url, status,
            data.get("name", "—") if isinstance(data, dict) else "—",
        )
        return {"success": True, "status": status, "data": data}

    error_msg = _parse_erp_error(status, body)

    if status in _NO_RETRY_STATUSES:
        activity.logger.warning(
            "  ❌ step %d: %s %s → %s — %s (non-retryable)",
            step_num, method, url, status, error_msg,
        )
        raise ValueError(f"HTTP {status}: {error_msg}")

    activity.logger.warning(
        "  ⚠️  step %d: %s %s → %s — %s (will retry)",
        step_num, method, url, status, error_msg,
    )
    raise RuntimeError(f"HTTP {status}: {error_msg}")


# ── Main activity ──────────────────────────────────────────────────────────────

@activity.defn(name="execute_command")
async def execute_command(
    payload_bundle: dict,
    plan:           dict,
    context:        dict,
) -> dict:
    """
    Execution Agent activity.

    Iterates over every step in the PayloadBundle, fires the corresponding
    ERPNext REST call, and returns a structured result.

    Pipeline position: Agent 7 (after Confirmation Gate).
    Consumer: workflow checks success/error; passes result to Result Formatter.
    """
    t0 = time.monotonic()

    # ── Extract credentials from context ──────────────────────────────────────
    creds      = context.get("erp_credentials", {})
    erp_url    = creds.get("erp_url",    "http://localhost:8080")
    api_key    = creds.get("api_key",    "")
    api_secret = creds.get("api_secret", "")

    is_dummy = context.get("company_profile", {}).get("is_dummy", False)

    steps     = payload_bundle.get("steps", [])
    n_steps   = len(steps)
    doctype   = steps[0].get("doctype", "unknown") if steps else "unknown"
    action    = steps[0].get("action",  "unknown") if steps else "unknown"

    activity.logger.info(
        "execute_command: doctype=%s action=%s steps=%d erp_url=%s dummy=%s",
        doctype, action, n_steps, erp_url, is_dummy,
    )

    # ── Dummy / stub mode ──────────────────────────────────────────────────────
    # When IS (onboarding) is not complete, erp_credentials has placeholder
    # values. We return a realistic stub result so the pipeline keeps flowing.
    if is_dummy or api_key in ("", "REPLACE_WITH_REAL_KEY"):
        activity.logger.warning(
            "execute_command: dummy profile detected — returning stub result. "
            "Complete IS onboarding and set real ERP_URL / ERP_API_KEY / ERP_API_SECRET."
        )
        stub_name = f"STUB-{doctype[:2].upper()}-{str(hash(str(steps)))[-5:]}"
        elapsed   = int((time.monotonic() - t0) * 1000)
        return {
            "success":           True,
            "result":            {"name": stub_name, "doctype": doctype, "_stub": True},
            "steps_results":     [{"step": 1, "success": True, "doc_name": stub_name}],
            "execution_time_ms": elapsed,
            "error":             None,
        }

    # ── Real execution ─────────────────────────────────────────────────────────
    headers       = _build_headers(api_key, api_secret)
    steps_results = []
    last_result   = {}

    try:
        async with aiohttp.ClientSession() as session:
            for step in steps:
                step_num    = step.get("step_number", 1)
                http_method = step.get("http_method", "POST").upper()
                endpoint    = step.get("endpoint", "")
                step_payload = step.get("payload", {})
                step_action  = step.get("action", "create")
                step_doctype = step.get("doctype", "")

                # Build URL — handle delete/get that need document name in path
                url = _erp_url(erp_url, endpoint)
                if step_action in ("update", "delete", "get"):
                    doc_name = step_payload.pop("name", None) or step_payload.pop("document_name", None)
                    if doc_name:
                        url = f"{url}/{quote(str(doc_name), safe='')}"

                step_result = await _call_erpnext(
                    session, http_method, url, headers, step_payload, step_num,
                )

                steps_results.append({
                    "step":     step_num,
                    "doctype":  step_doctype,
                    "action":   step_action,
                    "success":  step_result["success"],
                    "doc_name": step_result["data"].get("name", "") if isinstance(step_result.get("data"), dict) else "",
                    "data":     step_result.get("data"),
                })
                last_result = step_result.get("data", {})

    except ValueError as e:
        # 4xx — non-retryable, surface to user
        elapsed = int((time.monotonic() - t0) * 1000)
        activity.logger.error("execute_command failed (non-retryable): %s", e)
        return {
            "success":           False,
            "result":            {},
            "steps_results":     steps_results,
            "execution_time_ms": elapsed,
            "error":             {"message": str(e), "retryable": False},
        }

    except Exception as e:
        # 5xx / network — re-raise so Temporal retries
        activity.logger.warning("execute_command failed (retryable): %s", e)
        raise

    elapsed = int((time.monotonic() - t0) * 1000)

    activity.logger.info(
        "execute_command: ✅ completed %d step(s) in %dms — doc=%s",
        n_steps, elapsed,
        last_result.get("name", "—") if isinstance(last_result, dict) else "—",
    )

    return {
        "success":           True,
        "result":            last_result,
        "steps_results":     steps_results,
        "execution_time_ms": elapsed,
        "error":             None,
    }