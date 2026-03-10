"""Validation Agent: Check mandatory fields, customer/item exist."""
from typing import Any


def validate_sales_order_payload(payload: dict, context: dict) -> dict[str, Any]:
    """
    Validate Sales Order payload before execution.
    Returns: { valid: bool, errors: [], warnings: [] }
    """
    errors = []
    warnings = []

    # Mandatory fields
    if not payload.get("customer"):
        errors.append("customer is required")
    if not payload.get("items"):
        errors.append("items is required")
    elif not isinstance(payload["items"], list):
        errors.append("items must be a list")
    else:
        for i, row in enumerate(payload["items"]):
            if not row.get("item_code"):
                errors.append(f"items[{i}]: item_code is required")
            if row.get("qty") is None or (isinstance(row.get("qty"), (int, float)) and row["qty"] <= 0):
                errors.append(f"items[{i}]: qty must be > 0")

    if not payload.get("transaction_date"):
        errors.append("transaction_date is required")
    if not payload.get("delivery_date"):
        warnings.append("delivery_date not set, using transaction_date")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
