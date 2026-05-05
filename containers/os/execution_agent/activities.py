"""
containers/OS/execution_agent/activities.py

Temporal activity for the Execution Agent.
Registered on: os-main-queue (via os_worker.py)

Activity name: "execute_command"  ← must match workflow.py call exactly

NOW USES ERPAdapter for all ERP operations — no direct HTTP calls.

Input:
  payload_bundle dict  — from Payload Generator
    {
      "steps": [
        {
          "step_number": 1,
          "action":      "create",
          "doctype":     "Sales Order",
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

from temporalio import activity

from shared.erp_adapters.registry import get_adapter

logger = logging.getLogger(__name__)

# ── HTTP status codes that should NOT be retried (handled by adapter now) ─────
# Kept for reference but adapter handles this internally
_NO_RETRY_STATUSES = {400, 401, 403, 404, 409, 417, 422}

# ── Master data doctypes that need duplicate-existence check before POST ──────
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


# ── Pre-flight duplicate check for master data ───────────────────────────────

async def _check_master_exists(
    adapter,
    doctype: str,
    payload: dict,
) -> str | None:
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

    try:
        existing = await adapter.get_record(doctype, str(candidate_name), fields=["name"])
        if existing and existing.get("name"):
            return str(existing["name"])
    except ValueError:
        # 404 not found — safe to create
        return None
    except Exception:
        # Other errors — let POST proceed and surface ERPNext's own error
        return None

    return None


# ── Per-step executor using ERPAdapter ────────────────────────────────────────

async def _execute_step(
    adapter,
    step: dict,
) -> dict:
    """
    Execute a single step using ERPAdapter.
    
    Raises:
        ValueError — on non-retryable errors (4xx)
        RuntimeError — on retryable errors (5xx, network)
    """
    step_num = step.get("step_number", 1)
    step_action = step.get("action", "create")
    step_doctype = step.get("doctype", "")
    step_payload = dict(step.get("payload", {}))

    activity.heartbeat(f"Executing step {step_num}: {step_action} {step_doctype}")

    try:
        # ── CREATE ────────────────────────────────────────────────────────────
        if step_action == "create":
            # Pre-flight duplicate check for master data
            if step_doctype in _MASTER_DATA_DOCTYPES:
                existing = await _check_master_exists(adapter, step_doctype, step_payload)
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

            data = await adapter.create_record(step_doctype, step_payload)
            activity.logger.info(
                "  ✅ step %d: created %s → %s",
                step_num, step_doctype, data.get("name", "—"),
            )
            return {"success": True, "data": data}

        # ── UPDATE ────────────────────────────────────────────────────────────
        elif step_action == "update":
            doc_name = step_payload.pop("name", None) or step_payload.pop("docname", None)
            if not doc_name:
                raise ValueError(f"Update action requires 'name' field in payload")
            
            data = await adapter.update_record(step_doctype, str(doc_name), step_payload)
            activity.logger.info(
                "  ✅ step %d: updated %s/%s",
                step_num, step_doctype, doc_name,
            )
            return {"success": True, "data": data}

        # ── SUBMIT ────────────────────────────────────────────────────────────
        elif step_action == "submit":
            doc_name = step_payload.get("docname") or step_payload.get("name")
            if not doc_name:
                raise ValueError(f"Submit action requires 'docname' or 'name' field")
            
            data = await adapter.submit_document(step_doctype, str(doc_name))
            activity.logger.info(
                "  ✅ step %d: submitted %s/%s",
                step_num, step_doctype, doc_name,
            )
            return {"success": True, "data": data}

        # ── CANCEL ────────────────────────────────────────────────────────────
        elif step_action == "cancel":
            doc_name = step_payload.get("docname") or step_payload.get("name")
            if not doc_name:
                raise ValueError(f"Cancel action requires 'docname' or 'name' field")
            
            data = await adapter.cancel_document(step_doctype, str(doc_name))
            activity.logger.info(
                "  ✅ step %d: cancelled %s/%s",
                step_num, step_doctype, doc_name,
            )
            return {"success": True, "data": data}

        # ── GET ───────────────────────────────────────────────────────────────
        elif step_action in ("get", "get_document"):
            doc_name = step_payload.get("docname") or step_payload.get("name")
            if not doc_name:
                raise ValueError(f"Get action requires 'docname' or 'name' field")
            
            fields = step_payload.get("fields")
            data = await adapter.get_record(step_doctype, str(doc_name), fields=fields)
            activity.logger.info(
                "  ✅ step %d: fetched %s/%s",
                step_num, step_doctype, doc_name,
            )
            return {"success": True, "data": data}

        # ── SEARCH/LIST ───────────────────────────────────────────────────────
        elif step_action == "search":
            filters = step_payload.get("filters", [])
            fields = step_payload.get("fields", ["name", "status"])
            limit = step_payload.get("limit", 20)
            
            data = await adapter.list_records(
                step_doctype,
                fields=fields,
                filters=filters,
                limit=limit,
            )
            activity.logger.info(
                "  ✅ step %d: searched %s → %d results",
                step_num, step_doctype, len(data),
            )
            return {"success": True, "data": data}

        # ── DELETE ────────────────────────────────────────────────────────────
        elif step_action == "delete":
            doc_name = step_payload.get("docname") or step_payload.get("name")
            if not doc_name:
                raise ValueError(f"Delete action requires 'docname' or 'name' field")
            
            success = await adapter.delete_record(step_doctype, str(doc_name))
            activity.logger.info(
                "  ✅ step %d: deleted %s/%s",
                step_num, step_doctype, doc_name,
            )
            return {"success": True, "data": {"name": doc_name, "deleted": success}}

        # ── UNKNOWN ACTION ────────────────────────────────────────────────────
        else:
            raise ValueError(f"Unknown action: {step_action}")

    except ValueError as e:
        # Non-retryable client errors (4xx)
        activity.logger.error("  ❌ step %d: %s (non-retryable)", step_num, e)
        raise

    except RuntimeError as e:
        # Retryable server errors (5xx)
        activity.logger.warning("  ⚠️  step %d: %s (will retry)", step_num, e)
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

    Iterates over every step in the PayloadBundle, executes via ERPAdapter,
    and returns a structured result.

    Pipeline position: Agent 7 (after Confirmation Gate).
    Consumer: workflow checks success/error; passes result to Result Formatter.
    """
    t0 = time.monotonic()

    # ── Extract credentials from context ──────────────────────────────────────
    creds      = context.get("erp_credentials", {})
    erp_url    = creds.get("erp_url",    "http://localhost:8080")
    api_key    = creds.get("api_key",    "")
    api_secret = creds.get("api_secret", "")
    verify_ssl = creds.get("verify_ssl", True)
    allow_insecure_ssl = creds.get("allow_insecure_ssl", True)

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

    # ── Real execution via ERPAdapter ─────────────────────────────────────────
    
    # Build adapter profile
    profile = {
        "erp_type":           "erpnext",
        "erp_url":            erp_url,
        "api_key":            api_key,
        "api_secret":         api_secret,
        "verify_ssl":         verify_ssl,
        "allow_insecure_ssl": allow_insecure_ssl,
    }

    adapter = get_adapter(profile)

    steps_results = []
    last_result   = {}

    try:
        for step in steps:
            step_num = step.get("step_number", 1)
            step_action = step.get("action", "create")
            step_doctype = step.get("doctype", "")

            step_result = await _execute_step(adapter, step)

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
