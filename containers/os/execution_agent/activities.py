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
import ssl
import time
from urllib.parse import quote

import aiohttp
from temporalio import activity

logger = logging.getLogger(__name__)

# ── HTTP status codes that should NOT be retried ──────────────────────────────
_NO_RETRY_STATUSES = {400, 401, 403, 404, 409, 417, 422}

# ── Master data doctypes that need duplicate-existence check before POST ───────
# ERPNext auto-renames on duplicate (e.g. "Stark Industries" → "Stark Industries - 1")
# instead of erroring, so we must check first.
_MASTER_DATA_DOCTYPES: set[str] = {
    "Customer", "Supplier", "Item", "Warehouse", "Territory",
    "Customer Group", "Supplier Group", "Item Group",
    "Brand", "UOM", "Company", "Department", "Designation",
    "Sales Person", "Price List", "Payment Terms",
}

# Field that holds the human-readable name for each master doctype
_MASTER_NAME_FIELD: dict[str, str] = {
    "Customer":       "customer_name",
    "Supplier":       "supplier_name",
    "Item":           "item_code",
    "Warehouse":      "warehouse_name",
    "Territory":      "territory_name",
    "Customer Group": "customer_group_name",
    "Supplier Group": "supplier_group",
    "Item Group":     "item_group_name",
    "Brand":          "brand",
    "UOM":            "uom_name",
    "Company":        "company_name",
    "Department":     "department_name",
    "Designation":    "designation_name",
}


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


def _to_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_ssl_verification_error(exc: Exception) -> bool:
    ssl_error_types = (
        aiohttp.ClientConnectorCertificateError,
        aiohttp.ClientConnectorSSLError,
        aiohttp.ClientSSLError,
        ssl.SSLCertVerificationError,
    )

    if isinstance(exc, ssl_error_types):
        return True

    message = str(exc)
    return "CERTIFICATE_VERIFY_FAILED" in message or "self-signed certificate" in message


# ── Pre-flight duplicate check for master data ───────────────────────────────

async def _check_master_exists(
    session:  aiohttp.ClientSession,
    base_url: str,
    doctype:  str,
    payload:  dict,
    headers:  dict,
) -> "str | None":
    """
    Check if a master data record with the same name already exists before POSTing.
    ERPNext silently renames duplicates (Stark Industries -> Stark Industries - 1)
    instead of returning an error, so we must detect this ourselves.
    Returns the existing doc name if found, None if safe to create.
    """
    name_field = _MASTER_NAME_FIELD.get(doctype)
    if not name_field:
        return None

    candidate_name = payload.get(name_field) or payload.get("name")
    if not candidate_name:
        return None

    check_url = (
        base_url.rstrip("/")
        + "/api/resource/"
        + quote(doctype, safe="")
        + "/"
        + quote(str(candidate_name), safe="")
    )

    try:
        async with session.get(
            check_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                body = await resp.json(content_type=None)
                existing_name = body.get("data", {}).get("name", candidate_name)
                return str(existing_name)
            return None   # 404 = doesn't exist, anything else = ignore
    except Exception:
        return None   # If check fails, let POST proceed and surface ERPNext's own error


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


# ── Per-step executor with SSL fallback ───────────────────────────────────────

async def _execute_step(
    erp_url: str,
    headers: dict,
    step: dict,
    verify_ssl: bool,
    allow_insecure_ssl: bool,
) -> dict:
    async def _run_once(use_verify_ssl: bool) -> dict:
        connector = None if use_verify_ssl else aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            step_num = step.get("step_number", 1)
            http_method = step.get("http_method", "POST").upper()
            endpoint = step.get("endpoint", "")
            step_payload = dict(step.get("payload", {}))
            step_action = step.get("action", "create")
            step_doctype = step.get("doctype", "")

            url = _erp_url(erp_url, endpoint)
            if step_action in ("update", "delete", "get"):
                doc_name = step_payload.pop("name", None) or step_payload.pop("document_name", None)
                if doc_name:
                    url = f"{url}/{quote(str(doc_name), safe='')}"

            if step_action == "create" and step_doctype in _MASTER_DATA_DOCTYPES:
                existing = await _check_master_exists(
                    session, erp_url, step_doctype, step_payload, headers,
                )
                if existing:
                    name_field = _MASTER_NAME_FIELD.get(step_doctype, "name")
                    candidate = step_payload.get(name_field) or step_payload.get("name", "")
                    activity.logger.warning(
                        "  ⚠️  step %d: duplicate check — %s '%s' already exists as '%s'",
                        step_num, step_doctype, candidate, existing,
                    )
                    raise ValueError(
                        f"DuplicateEntryError: '{candidate}' already exists as '{existing}' "
                        f"in {step_doctype}. Open the existing record or use a different name."
                    )

            return await _call_erpnext(
                session, http_method, url, headers, step_payload, step_num,
            )

    try:
        return await _run_once(verify_ssl)
    except Exception as exc:
        if verify_ssl and allow_insecure_ssl and _is_ssl_verification_error(exc):
            activity.logger.warning(
                "SSL verification failed for %s — retrying once with certificate checks disabled",
                erp_url,
            )
            return await _run_once(False)
        raise


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
    verify_ssl = _to_bool(creds.get("verify_ssl"), True)
    allow_insecure_ssl = _to_bool(creds.get("allow_insecure_ssl"), True)

    is_dummy = context.get("company_profile", {}).get("is_dummy", False)

    steps     = payload_bundle.get("steps", [])
    n_steps   = len(steps)
    doctype   = steps[0].get("doctype", "unknown") if steps else "unknown"
    action    = steps[0].get("action",  "unknown") if steps else "unknown"

    activity.logger.info(
        "execute_command: doctype=%s action=%s steps=%d erp_url=%s dummy=%s verify_ssl=%s allow_insecure_ssl=%s",
        doctype, action, n_steps, erp_url, is_dummy, verify_ssl, allow_insecure_ssl,
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
        for step in steps:
            step_num = step.get("step_number", 1)
            step_action = step.get("action", "create")
            step_doctype = step.get("doctype", "")

            step_result = await _execute_step(
                erp_url=erp_url,
                headers=headers,
                step=step,
                verify_ssl=verify_ssl,
                allow_insecure_ssl=allow_insecure_ssl,
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