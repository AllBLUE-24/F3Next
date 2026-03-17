"""Result Formatter: API response → human-readable message."""
from typing import Any


def format_success(result: dict, erp_url: str = "") -> str:
    """Format successful Sales Order creation. Includes ERP deep-link per architecture."""
    name = result.get("name", "SO-?????")
    customer = result.get("customer", "")
    grand_total = result.get("grand_total", 0)
    docstatus = result.get("docstatus", 0)
    status = "Submitted" if docstatus == 1 else "Draft"
    is_demo = "DEMO" in str(name).upper()

    demo_banner = "\n(Demo mode — no ERPNext. Set DEMO_MODE=false in .env to use real ERP.)\n\n" if is_demo else ""

    link_line = ""
    if erp_url and not is_demo:
        link_line = f"- View in ERPNext: {erp_url}/app/sales-order/{name}\n\n"

    return f"""Sales Order {name} created successfully.{demo_banner}
Details:
• Customer: {customer}
• Total: Rs {grand_total:,.2f}
• Status: {status}

Next steps:
- Submit this order to confirm
- Create Delivery Note when ready to ship
{link_line}"""


def format_error(error: str) -> str:
    """Format error message for user."""
    err_lower = str(error).lower()
    if "connection refused" in err_lower or "10061" in err_lower or "actively refused" in err_lower:
        return f"""Could not create Sales Order.

Reason: ERPNext is not reachable (connection refused).

This usually means:
1. ERPNext is not running — start it with: bench start
2. Wrong URL in .env — check ERPNEXT_URL (e.g. http://localhost:8000)
3. ERPNext is on a different port — update .env with the correct URL"""
    return f"""Could not create Sales Order.

Reason: {error}

What you can do:
1. Check that the customer and items exist in ERPNext
2. Verify API credentials in .env
3. Ensure ERPNext URL is correct and accessible"""


def format_result(execution_result: dict[str, Any], erp_url: str = "") -> str:
    """Format execution result (success or error) for user."""
    if execution_result.get("success"):
        return format_success(execution_result.get("result", {}), erp_url)
    return format_error(execution_result.get("error", "Unknown error"))
