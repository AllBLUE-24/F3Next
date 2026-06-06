"""MVP-scoped gap analyzer tests — Green Surface 3rd_run golden fixtures."""
from __future__ import annotations

from containers.implementation.data_readiness_agent.gap_analyzer import analyze_gaps
from containers.implementation.file_io.manifest_utils import build_manifest_v2
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings

THIRD_RUN_FILES = {
    "messy_partners.csv": (
        "Company_Name,Role,City,Contact\r\n"
        "Rohan Construction,Customer,Mumbai,Rohan\r\n"
        "Gupta Chemical Traders,Supplier,Ahmedabad,S.K. Gupta\r\n"
        "Ultra Floors Pvt Ltd,Customer,Pune,\r\n"
        "Karan Acids & Solvents,Vendor,Nagpur,Karan"
    ),
    "client_orders.csv": (
        "Client,Project,Target_Date,Product,Vol,Price\r\n"
        "Rohan Construction,PRJ-Mumbai-Mall,2026-08-15,SRV-INSTALL,12000,\r\n"
        "New Age Builders,PRJ-Pune-ITPark,2026-09-01,FG-PRIMER-A,200,52.00"
    ),
    "raw_purchase_orders.csv": (
        "PO_Number,Vendor_Name,Item,Ordered_Qty,Price_Per_Unit\r\n"
        "PO-26-001,Gupta Chemical Traders,RM-EPOX-LIQ,2000,4.60\r\n"
        "PO-26-002,Karan Acids & Solvents,RM-SOLVENT-X,400,\r\n"
        "PO-26-003,Unknown Supplier Ltd,RM-HARD-AMN,100,9.00"
    ),
}

# Mirrors production mvp_boundary.json seed_doctypes_chosen (pre-refine)
ACTUAL_MVP_SEEDS = [
    "Project",
    "Item",
    "Stock Entry",
    "Purchase Order",
    "Sales Order",
    "Item Variant",
    "Task",
    "Timesheet",
    "Quotation",
    "Delivery Note",
]

DEFERRED = ["Batch", "BOM", "Work Order", "Job Card"]


def _corpus():
    return {
        "corpus_summary": "Party master, client orders, purchase orders",
        "files": [
            {
                "filename": "messy_partners.csv",
                "likely_erpnext_doctypes": ["Customer", "Supplier"],
            },
            {
                "filename": "client_orders.csv",
                "likely_erpnext_doctypes": ["Sales Order", "Project", "Customer"],
                "explicitly_not_doctypes": ["Work Order", "BOM"],
            },
            {
                "filename": "raw_purchase_orders.csv",
                "likely_erpnext_doctypes": ["Purchase Order", "Supplier", "Item"],
            },
        ],
    }


def _target_structure(seeds=None):
    seeds = seeds or ACTUAL_MVP_SEEDS
    return {
        "seed_doctypes": seeds,
        "deferred_doctypes": DEFERRED,
        "required_doctypes": seeds + ["Company", "Warehouse", "UOM"],
        "setup_steps": [
            {"doctype": "Project", "phase": "phase_d_projects", "action": "must_create"},
            {"doctype": "Item", "phase": "phase_b_master", "action": "must_create"},
            {"doctype": "Stock Entry", "phase": "phase_c_transactional", "action": "must_create"},
            {"doctype": "Purchase Order", "phase": "phase_c_transactional", "action": "must_create"},
            {"doctype": "Sales Order", "phase": "phase_c_transactional", "action": "must_create"},
            {"doctype": "Task", "phase": "phase_d_projects", "action": "must_create"},
            {"doctype": "Timesheet", "phase": "phase_d_projects", "action": "must_create"},
            {"doctype": "Item Variant", "phase": "phase_b_master", "action": "must_create"},
            {"doctype": "Quotation", "phase": "phase_c_transactional", "action": "must_create"},
            {"doctype": "Delivery Note", "phase": "phase_c_transactional", "action": "must_create"},
        ],
        "import_phases": {},
    }


def _analyze(seeds=None):
    manifest = build_manifest_v2(THIRD_RUN_FILES, created_at="2026-06-05T00:00:00Z")
    manifest["corpus_understanding"] = _corpus()
    return analyze_gaps(manifest, _target_structure(seeds), _kb_field_mappings())


def test_party_masters_injected_when_missing_from_seeds():
    """Legacy target structures without Customer/Supplier still get party coverage."""
    result = _analyze()
    ready = {r["doctype"]: r for r in result["ready_doctypes"]}
    assert "Customer" in ready
    assert "Supplier" in ready


def test_project_ready_with_embedded_transactional_note():
    result = _analyze()
    ready = {r["doctype"]: r for r in result["ready_doctypes"]}
    assert "Project" in ready
    project = ready["Project"]
    assert project.get("evidence_type") == "embedded_in_transactional"
    assert project.get("ready_with_assumptions") is True
    assert project.get("source_file") == "client_orders.csv"


def test_core_transactional_doctypes_ready():
    result = _analyze()
    ready = {r["doctype"]: r for r in result["ready_doctypes"]}
    assert "Item" in ready
    assert "Purchase Order" in ready
    assert "Sales Order" in ready
    for dt in ("Purchase Order", "Sales Order", "Customer", "Supplier"):
        assert ready[dt].get("dry_run_passed") is True, f"{dt} should pass dry-run preflight"


def test_dry_run_ready_count_in_summary():
    result = _analyze()
    summary = result["summary"]
    assert summary.get("n_dry_run_ready", 0) >= 6
    assert summary["n_dry_run_ready"] <= summary["n_ready"]


def test_stock_entry_missing_from_upload():
    result = _analyze()
    missing = [m["doctype"] for m in result["missing_doctypes"]]
    assert "Stock Entry" in missing


def test_deferred_doctypes_not_scanned():
    result = _analyze()
    all_doctypes = (
        [r["doctype"] for r in result["ready_doctypes"]]
        + [p["doctype"] for p in result["partial_doctypes"]]
        + [m["doctype"] for m in result["missing_doctypes"]]
    )
    for deferred in DEFERRED:
        assert deferred not in all_doctypes


def test_readiness_score_reflects_covered_seeds():
    result = _analyze()
    summary = result["summary"]
    assert summary["mvp_scoped"] is True
    assert summary["n_ready"] >= 6
    assert summary["raw_readiness_score"] >= 0.5
