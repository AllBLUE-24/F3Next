"""3rd_run golden assess tests."""
from __future__ import annotations

from containers.implementation.file_io.manifest_utils import build_manifest_v2
from containers.implementation.readiness.assess import assess_readiness
from containers.implementation.readiness.inputs import build_readiness_inputs

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

ACTUAL_MVP_SEEDS = [
    "Project",
    "Item",
    "Stock Entry",
    "Purchase Order",
    "Sales Order",
    "Task",
    "Timesheet",
    "Item Variant",
    "Quotation",
    "Delivery Note",
]

DEFERRED = ["Batch", "BOM", "Work Order", "Job Card"]


def _corpus():
    return {
        "corpus_summary": "Party master, client orders, purchase orders",
        "files": [
            {"filename": "messy_partners.csv", "likely_erpnext_doctypes": ["Customer", "Supplier"]},
            {
                "filename": "client_orders.csv",
                "likely_erpnext_doctypes": ["Sales Order", "Project", "Customer"],
                "explicitly_not_doctypes": ["Work Order", "BOM"],
            },
            {"filename": "raw_purchase_orders.csv", "likely_erpnext_doctypes": ["Purchase Order", "Supplier", "Item"]},
        ],
    }


def _target():
    return {
        "seed_doctypes": ACTUAL_MVP_SEEDS,
        "deferred_doctypes": DEFERRED,
        "required_doctypes": ACTUAL_MVP_SEEDS + ["Company", "Warehouse", "UOM"],
        "setup_steps": [
            {"doctype": "Project", "phase": "phase_d_projects", "action": "must_create"},
            {"doctype": "Item", "phase": "phase_b_master", "action": "must_create"},
            {"doctype": "Stock Entry", "phase": "phase_c_transactional", "action": "must_create"},
            {"doctype": "Purchase Order", "phase": "phase_c_transactional", "action": "must_create"},
            {"doctype": "Sales Order", "phase": "phase_c_transactional", "action": "must_create"},
        ],
    }


def _report():
    manifest = build_manifest_v2(THIRD_RUN_FILES, created_at="2026-06-05T00:00:00Z")
    manifest["corpus_understanding"] = _corpus()
    inputs = build_readiness_inputs(
        project_id="test-project",
        manifest=manifest,
        target_structure=_target(),
    )
    return assess_readiness(inputs)


def test_assess_returns_matrix_rows():
    report = _report()
    assert len(report.matrix.rows) > 0
    assert report.schema_sources


def test_party_masters_ready_on_3rd_run():
    report = _report()
    ready = {r.doctype for r in report.ready_doctypes}
    assert "Customer" in ready
    assert "Supplier" in ready


def test_readiness_level_matches_gap_analyzer_honesty():
    report = _report()
    mvp = report.pre_analysis.get("summary", {}).get("minimum_viable_possible")
    if mvp is False:
        assert report.readiness_level == "red"
        assert report.minimum_viable_import_possible is False
    else:
        assert report.readiness_level in ("green", "yellow")
