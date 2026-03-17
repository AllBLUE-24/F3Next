"""3-phase import engine — Config → Master → Transactional."""
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class ImportPhase(str, Enum):
    PHASE_A_CONFIG = "phase_a_config"
    PHASE_B_MASTER = "phase_b_master"
    PHASE_C_TRANSACTIONAL = "phase_c_transactional"
    COMPLETE = "complete"


class ImportEngine:
    """
    3-phase import:
    Phase A: Configuration (COA, Groups, Warehouses, Tax, Fiscal Year, Company)
    Phase B: Master data (Items, Customers, Suppliers, BOMs)
    Phase C: Transactional (Opening balances, historical transactions)
    """

    PHASE_A_DOCTYPES = [
        "Company", "Fiscal Year", "Currency", "UOM",
        "Account", "Item Group", "Customer Group", "Supplier Group",
        "Warehouse", "Tax Template",
    ]
    PHASE_B_DOCTYPES = ["Item", "Customer", "Supplier", "Item Price", "BOM"]
    PHASE_C_DOCTYPES = ["Stock Entry", "Journal Entry", "Purchase Invoice", "Sales Invoice", "Payment Entry"]

    def __init__(self, erpnext_client: Optional[Any] = None):
        """
        erpnext_client: Optional client to call ERPNext API.
        If None, engine produces import plan only (no actual API calls).
        """
        self.erpnext_client = erpnext_client

    def build_import_plan(
        self,
        target_structure: Dict,
        mapped_data: Dict[str, Any],
        validation_report: Dict,
    ) -> Dict[str, Any]:
        """
        Build the full 3-phase import plan.
        Returns ordered steps with data to import.
        """
        if validation_report.get("overall") == "fail":
            return {
                "status": "blocked",
                "reason": "Validation failed. Fix errors before import.",
                "validation_report": validation_report,
            }

        plan = {
            "status": "ready",
            "phases": [],
            "total_steps": 0,
        }

        # Phase A
        phase_a = {
            "phase": "phase_a_config",
            "name": "Configuration Setup",
            "description": "Chart of Accounts, Groups, Warehouses, Tax Templates, Fiscal Year, Company settings",
            "steps": [],
            "doctypes": self.PHASE_A_DOCTYPES,
        }
        for dt in self.PHASE_A_DOCTYPES:
            if dt in mapped_data:
                phase_a["steps"].append({
                    "doctype": dt,
                    "data": mapped_data[dt],
                    "action": "create",
                })
            else:
                phase_a["steps"].append({
                    "doctype": dt,
                    "data": None,
                    "action": "default_or_skip",
                })
        plan["phases"].append(phase_a)

        # Phase B
        phase_b = {
            "phase": "phase_b_master",
            "name": "Master Data",
            "description": "Items, Customers, Suppliers, BOMs (if manufacturing)",
            "steps": [],
            "doctypes": self.PHASE_B_DOCTYPES,
        }
        required = target_structure.get("required_doctypes", [])
        for dt in self.PHASE_B_DOCTYPES:
            if dt not in required:
                continue
            if dt in mapped_data:
                phase_b["steps"].append({
                    "doctype": dt,
                    "data": mapped_data[dt],
                    "action": "create",
                })
        plan["phases"].append(phase_b)

        # Phase C
        phase_c = {
            "phase": "phase_c_transactional",
            "name": "Transactional Data",
            "description": "Opening balances, historical transactions (last 3 months optional)",
            "steps": [],
            "doctypes": self.PHASE_C_DOCTYPES,
        }
        for dt in self.PHASE_C_DOCTYPES:
            if dt in mapped_data:
                phase_c["steps"].append({
                    "doctype": dt,
                    "data": mapped_data[dt],
                    "action": "create",
                })
        plan["phases"].append(phase_c)

        plan["total_steps"] = sum(
            len(p["steps"]) for p in plan["phases"]
        )

        return plan

    def execute_phase(
        self,
        phase_id: str,
        steps: List[Dict],
    ) -> Dict[str, Any]:
        """
        Execute a single phase.
        If erpnext_client is set, calls API. Otherwise returns dry-run result.
        """
        results = []
        for step in steps:
            if self.erpnext_client:
                # Would call: self.erpnext_client.create_doc(step["doctype"], step["data"])
                result = {"doctype": step["doctype"], "status": "simulated", "created": 0}
            else:
                row_count = 0
                if step.get("data"):
                    rows = step["data"].get("rows", step["data"].get("data", []))
                    row_count = len(rows) if isinstance(rows, list) else 0
                result = {
                    "doctype": step["doctype"],
                    "status": "dry_run",
                    "would_create": row_count,
                    "message": "No ERPNext client configured. Run with client for actual import.",
                }
            results.append(result)

        return {
            "phase": phase_id,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
