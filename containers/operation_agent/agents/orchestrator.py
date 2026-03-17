"""Orchestrator: Chain agents per erp_os_architecture.md flow."""
from typing import Any

from config import ERPNEXT_URL
from agents.clarity_agent import process_prompt
from agents.command_planning import get_execution_plan
from agents.context_retrieval import get_context
from agents.execution_agent import execute_sales_order
from agents.payload_generator import build_sales_order_payload
from agents.result_formatter import format_result
from agents.validation_agent import validate_sales_order_payload


def run_create_sales_order(prompt: str) -> dict[str, Any]:
    """
    Full pipeline per erp_os_architecture.md:
    Clarity → Context → Command Planning → Payload → Validation → Execution → Result Formatter
    Returns: { success: bool, message: str, data?: {...} }
    """
    try:
        clarity = process_prompt(prompt)
    except Exception as e:
        return {"success": False, "message": f"Could not parse command: {e}", "data": None}

    intent = clarity.get("intent", "")
    if intent != "create_sales_order":
        return {
            "success": False,
            "message": f"Unsupported intent: {intent}. Only 'create_sales_order' is supported.",
            "data": {"intent": intent},
        }

    entities = clarity.get("entities", {})
    context = get_context(intent, entities)
    plan = get_execution_plan(intent, context)

    if not plan.get("steps"):
        return {"success": False, "message": "No execution plan for this intent.", "data": None}

    payload = build_sales_order_payload(clarity, context)

    validation = validate_sales_order_payload(payload, context)
    if not validation["valid"]:
        errs = "; ".join(validation["errors"])
        return {"success": False, "message": f"Validation failed: {errs}", "data": {"errors": validation["errors"]}}

    execution = execute_sales_order(payload, clarity_entities=entities)
    message = format_result(execution, erp_url=ERPNEXT_URL or "")

    return {
        "success": execution["success"],
        "message": message,
        "data": execution.get("result") if execution["success"] else None,
    }
