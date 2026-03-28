"""
Import Agent — Temporal activities for the 3-phase ERPNext import.
Moved from: backend/app/services/implementation/import_engine.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from temporalio import activity


# ── Embedded service logic ────────────────────────────────────────────────────

class _ImportEngine:
    PHASE_A_DOCTYPES = [
        "Company", "Fiscal Year", "Currency", "UOM",
        "Account", "Item Group", "Customer Group", "Supplier Group",
        "Warehouse", "Tax Template",
    ]
    PHASE_B_DOCTYPES = ["Item", "Customer", "Supplier", "Item Price", "BOM"]
    PHASE_C_DOCTYPES = ["Stock Entry", "Journal Entry", "Purchase Invoice", "Sales Invoice", "Payment Entry"]

    def build_plan(
        self,
        target_structure: Dict,
        mapped_data: Dict[str, Any],
        validation_report: Dict,
    ) -> Dict[str, Any]:
        if validation_report.get("overall") == "fail":
            return {
                "status": "blocked",
                "reason": "Validation failed. Fix errors before import.",
                "validation_report": validation_report,
            }

        required = target_structure.get("required_doctypes", [])
        phases = []

        def _phase(phase_id: str, name: str, desc: str, doctypes: List[str], filter_required: bool = False) -> Dict:
            steps = []
            for dt in doctypes:
                if filter_required and dt not in required:
                    continue
                steps.append({
                    "doctype": dt,
                    "data": mapped_data.get(dt),
                    "action": "create" if dt in mapped_data else "default_or_skip",
                })
            return {"phase": phase_id, "name": name, "description": desc, "doctypes": doctypes, "steps": steps}

        phases.append(_phase(
            "phase_a_config", "Configuration Setup",
            "COA, Groups, Warehouses, Tax Templates, Fiscal Year, Company settings",
            self.PHASE_A_DOCTYPES,
        ))
        phases.append(_phase(
            "phase_b_master", "Master Data",
            "Items, Customers, Suppliers, BOMs (manufacturing only)",
            self.PHASE_B_DOCTYPES,
            filter_required=True,
        ))
        phases.append(_phase(
            "phase_c_transactional", "Transactional Data",
            "Opening balances, historical transactions (last 3 months optional)",
            self.PHASE_C_DOCTYPES,
        ))

        return {
            "status": "ready",
            "phases": phases,
            "total_steps": sum(len(p["steps"]) for p in phases),
        }

    def dry_run_phase(self, phase_id: str, steps: List[Dict]) -> Dict[str, Any]:
        results = []
        for step in steps:
            rows = 0
            if step.get("data"):
                d = step["data"]
                r = d.get("rows", d.get("data", []))
                rows = len(r) if isinstance(r, list) else 0
            results.append({
                "doctype": step["doctype"],
                "status": "dry_run",
                "would_create": rows,
            })
        return {"phase": phase_id, "results": results, "timestamp": datetime.utcnow().isoformat() + "Z"}


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class BuildImportPlanInput:
    target_structure: Dict[str, Any]
    mapped_data: Dict[str, Any]
    validation_report: Dict[str, Any]


@dataclass
class ExecutePhaseInput:
    phase_id: str
    steps: List[Dict[str, Any]]
    dry_run: bool = True           # False = real ERPNext API calls
    erpnext_base_url: Optional[str] = None
    erpnext_api_key: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="build_import_plan")
async def build_import_plan(inp: BuildImportPlanInput) -> Dict[str, Any]:
    """
    Produce the ordered 3-phase import plan.
    Returns: {status, phases, total_steps}  — or {status: "blocked"} on validation failure.
    """
    engine = _ImportEngine()
    return engine.build_plan(inp.target_structure, inp.mapped_data, inp.validation_report)


@activity.defn(name="execute_import_phase")
async def execute_import_phase(inp: ExecutePhaseInput) -> Dict[str, Any]:
    """
    Execute (or dry-run) a single import phase.
    In dry_run mode: counts rows without touching ERPNext.
    In live mode: POSTs each step to the ERPNext REST API.
    """
    engine = _ImportEngine()

    if inp.dry_run or not inp.erpnext_base_url:
        return engine.dry_run_phase(inp.phase_id, inp.steps)

    # ── Live ERPNext import ────────────────────────────────────────────────
    import httpx  # optional dep; only needed for live import

    results = []
    async with httpx.AsyncClient(base_url=inp.erpnext_base_url, timeout=30.0) as client:
        for step in inp.steps:
            if not step.get("data") or step.get("action") == "default_or_skip":
                results.append({"doctype": step["doctype"], "status": "skipped"})
                continue
            try:
                resp = await client.post(
                    f"/api/resource/{step['doctype']}",
                    json=step["data"],
                    headers={"Authorization": f"token {inp.erpnext_api_key}"},
                )
                resp.raise_for_status()
                results.append({"doctype": step["doctype"], "status": "created", "name": resp.json().get("data", {}).get("name")})
            except Exception as exc:
                results.append({"doctype": step["doctype"], "status": "error", "detail": str(exc)})

    return {"phase": inp.phase_id, "results": results, "timestamp": datetime.utcnow().isoformat() + "Z"}