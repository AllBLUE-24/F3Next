"""
Validation Agent — Temporal activities for pre-import data validation.
Moved from: backend/app/services/implementation/validation_engine.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from temporalio import activity


# ── Embedded service logic ────────────────────────────────────────────────────

class _ValidationEngine:
    REQUIRED_FIELDS: Dict[str, List[str]] = {
        "Item":             ["item_code", "item_name", "item_group", "stock_uom"],
        "Customer":         ["customer_name", "customer_type", "customer_group", "territory"],
        "Supplier":         ["supplier_name", "supplier_type", "supplier_group"],
        "Sales Invoice":    ["customer", "posting_date"],
        "Purchase Invoice": ["supplier", "bill_no", "bill_date"],
    }

    def validate(self, mapped_data: Dict[str, Any], target_structure: Dict[str, Any]) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "overall": "pass",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": [],
            "errors": [],
            "warnings": [],
        }
        required_doctypes = target_structure.get("required_doctypes", [])
        rules = target_structure.get("validation_rules", {})

        for dt, data in mapped_data.items():
            if dt not in required_doctypes:
                continue
            check = self._check_doctype(dt, data, rules)
            report["checks"].append(check)
            if check["status"] == "fail":
                report["errors"].extend(check["errors"])
                report["overall"] = "fail"
            report["warnings"].extend(check["warnings"])

        return report

    def _check_doctype(self, doctype: str, data: Dict, rules: Dict) -> Dict:
        check: Dict[str, Any] = {"doctype": doctype, "status": "pass", "errors": [], "warnings": [], "row_count": 0}
        rows = data.get("rows", data.get("data", []))
        check["row_count"] = len(rows) if isinstance(rows, list) else 0

        # Required-field check
        required = self.REQUIRED_FIELDS.get(doctype, [])
        if rows and required:
            sample = rows[0]
            for field in required:
                if field not in sample and not any(field in str(k) for k in sample.keys()):
                    check["errors"].append(f"Missing required field: {field}")
                    check["status"] = "fail"

        # Type sanity on first 10 rows
        for i, row in enumerate(rows[:10]):
            for k, v in row.items():
                if not v and v != 0:
                    continue
                if "date" in k.lower() and not self._is_date(str(v)):
                    check["warnings"].append(f"Row {i+1}: Invalid date format — {k}: {v}")
                if any(t in k.lower() for t in ("amount", "rate", "qty", "price")) and not self._is_numeric(str(v)):
                    check["warnings"].append(f"Row {i+1}: Non-numeric value — {k}: {v}")

        return check

    @staticmethod
    def _is_date(s: str) -> bool:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                datetime.strptime(s[:10], fmt)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _is_numeric(s: str) -> bool:
        return bool(re.match(r"^-?\d+\.?\d*$", s.replace(",", "").strip()))


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class ValidateInput:
    mapped_data: Dict[str, Any]       # {doctype: {rows: [...]}}
    target_structure: Dict[str, Any]  # from build_target_structure


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="validate_mapped_data")
async def validate_mapped_data(inp: ValidateInput) -> Dict[str, Any]:
    """
    Run pre-import validation checks on mapped data.
    Returns a validation report: {overall, checks, errors, warnings}
    """
    engine = _ValidationEngine()
    return engine.validate(inp.mapped_data, inp.target_structure)