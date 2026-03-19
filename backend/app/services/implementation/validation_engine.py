"""Validation engine — pre-import checks."""
from typing import Dict, List, Any, Optional
from datetime import datetime
import re


class ValidationEngine:
    """Validates mapped data before import."""

    def __init__(self, doctype_graph: Optional[Dict] = None):
        self.doctype_graph = doctype_graph or {}

    def validate_mapped_data(
        self,
        mapped_data: Dict[str, Any],
        target_structure: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run validation checks on mapped data.
        Returns validation report with pass/fail per entity.
        """
        report = {
            "overall": "pass",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": [],
            "errors": [],
            "warnings": [],
        }

        required_doctypes = target_structure.get("required_doctypes", [])
        validation_rules = target_structure.get("validation_rules", {})

        for dt, data in mapped_data.items():
            if dt not in required_doctypes:
                continue
            check = self._validate_doctype(dt, data, validation_rules)
            report["checks"].append(check)
            if check.get("status") == "fail":
                report["errors"].extend(check.get("errors", []))
                report["overall"] = "fail"
            report["warnings"].extend(check.get("warnings", []))

        return report

    def _validate_doctype(
        self,
        doctype: str,
        data: Dict,
        rules: Dict,
    ) -> Dict:
        """Validate a single doctype's data."""
        check = {
            "doctype": doctype,
            "status": "pass",
            "errors": [],
            "warnings": [],
            "row_count": 0,
        }

        rows = data.get("rows", data.get("data", []))
        if isinstance(rows, list):
            check["row_count"] = len(rows)
        else:
            check["row_count"] = 0

        # Required fields check
        required = self._get_required_fields(doctype)
        if rows and required:
            sample = rows[0] if rows else {}
            for field in required:
                if field not in sample and not any(field in str(k) for k in sample.keys()):
                    check["errors"].append(f"Missing required field: {field}")
                    check["status"] = "fail"

        # Data type checks (basic)
        for i, row in enumerate(rows[:10]):  # Sample first 10
            for k, v in row.items():
                if v is None or v == "":
                    continue
                if "date" in k.lower() and not self._is_valid_date(str(v)):
                    check["warnings"].append(f"Row {i+1}: Invalid date format for {k}: {v}")
                if "amount" in k.lower() or "rate" in k.lower() or "qty" in k.lower():
                    if not self._is_numeric(str(v)):
                        check["warnings"].append(f"Row {i+1}: Non-numeric value for {k}: {v}")

        # GST check if rule says so
        if rules.get("gst_required") and doctype in ("Customer", "Supplier", "Sales Invoice"):
            # Could add GSTIN format validation
            pass

        return check

    def _get_required_fields(self, doctype: str) -> List[str]:
        defaults = {
            "Item": ["item_code", "item_name", "item_group", "stock_uom"],
            "Customer": ["customer_name", "customer_type", "customer_group", "territory"],
            "Supplier": ["supplier_name", "supplier_type", "supplier_group"],
            "Sales Invoice": ["customer", "posting_date"],
            "Purchase Invoice": ["supplier", "bill_no", "bill_date"],
        }
        return defaults.get(doctype, [])

    def _is_valid_date(self, s: str) -> bool:
        try:
            datetime.strptime(s[:10], "%Y-%m-%d")
            return True
        except Exception:
            try:
                datetime.strptime(s[:10], "%d/%m/%Y")
                return True
            except Exception:
                return False

    def _is_numeric(self, s: str) -> bool:
        s = s.replace(",", "").strip()
        return bool(re.match(r"^-?\d+\.?\d*$", s))
