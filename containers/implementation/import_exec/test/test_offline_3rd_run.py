"""3rd_run offline import golden tests."""
from __future__ import annotations

from containers.implementation.file_io.manifest_utils import build_manifest_v2
from containers.implementation.import_exec.assess import assess_import_from_map_validate
from containers.implementation.map_validate.assess import assess_map_validate_offline
from containers.implementation.map_validate.inputs import build_map_validate_inputs

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

TARGET = {
    "seed_doctypes": [
        "Project", "Item", "Stock Entry", "Purchase Order", "Sales Order",
        "Customer", "Supplier",
    ],
    "deferred_doctypes": ["Batch", "BOM", "Work Order"],
    "required_doctypes": [
        "Project", "Item", "Purchase Order", "Sales Order", "Customer", "Supplier",
    ],
    "setup_steps": [
        {"doctype": "Customer", "phase": "phase_b_master", "action": "must_create"},
        {"doctype": "Supplier", "phase": "phase_b_master", "action": "must_create"},
        {"doctype": "Sales Order", "phase": "phase_c_transactional", "action": "must_create"},
        {"doctype": "Purchase Order", "phase": "phase_c_transactional", "action": "must_create"},
        {"doctype": "Project", "phase": "phase_d_projects", "action": "optional_if_absent"},
        {"doctype": "Item", "phase": "phase_b_master", "action": "optional_if_absent"},
        {"doctype": "Stock Entry", "phase": "phase_c_transactional", "action": "optional_if_absent"},
    ],
}


def _corpus():
    return {
        "files": [
            {"filename": "messy_partners.csv", "likely_erpnext_doctypes": ["Customer", "Supplier"]},
            {"filename": "client_orders.csv", "likely_erpnext_doctypes": ["Sales Order", "Project"]},
            {"filename": "raw_purchase_orders.csv", "likely_erpnext_doctypes": ["Purchase Order", "Item"]},
        ],
    }


def _map_validate_report():
    manifest = build_manifest_v2(THIRD_RUN_FILES, created_at="2026-06-05T00:00:00Z")
    files = manifest.get("files") or THIRD_RUN_FILES
    inputs = build_map_validate_inputs(
        project_id="test",
        files=files if isinstance(files, dict) and all(isinstance(v, str) for v in files.values()) else THIRD_RUN_FILES,
        target_structure=TARGET,
        corpus_understanding=_corpus(),
        company_context={"company_name": "Green Surface"},
    )
    return assess_map_validate_offline(inputs), inputs


def _import_report():
    mv_report, mv_inputs = _map_validate_report()
    from containers.implementation.map_validate.map_offline import run_offline_mapping

    _, mapped_data = run_offline_mapping(mv_inputs)
    return assess_import_from_map_validate(
        project_id="test",
        setup_steps=TARGET["setup_steps"],
        target_structure=TARGET,
        mapped_data=mapped_data,
        map_validate_report=mv_report,
    )


def test_offline_import_plan_not_blocked():
    report = _import_report()
    assert report.plan_status in ("ready", "ready_with_gaps")
    assert report.import_level in ("success", "partial")


def test_offline_import_has_core_create_steps():
    report = _import_report()
    create_doctypes = {s.doctype for s in report.steps if s.action == "create" and s.records > 0}
    assert "Customer" in create_doctypes
    assert "Supplier" in create_doctypes
    assert "Sales Order" in create_doctypes
    assert "Purchase Order" in create_doctypes


def test_import_ui_payload_shape():
    from containers.implementation.import_exec.import_ui import build_import_ui_from_report

    report = _import_report()
    ui = build_import_ui_from_report(report)
    assert ui["import_level"] in ("success", "partial", "failed", "blocked")
    assert "executive_summary" in ui
    assert "create_step_count" in ui


def test_phase_order_projects_before_transactional():
    report = _import_report()
    if "phase_d_projects" in report.ordered_phase_ids and "phase_c_transactional" in report.ordered_phase_ids:
        assert report.ordered_phase_ids.index("phase_d_projects") < report.ordered_phase_ids.index(
            "phase_c_transactional"
        )
