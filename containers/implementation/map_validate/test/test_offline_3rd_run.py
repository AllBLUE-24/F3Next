"""3rd_run offline map+validate golden tests."""
from __future__ import annotations

from containers.implementation.file_io.manifest_utils import build_manifest_v2
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
}


def _corpus():
    return {
        "files": [
            {"filename": "messy_partners.csv", "likely_erpnext_doctypes": ["Customer", "Supplier"]},
            {"filename": "client_orders.csv", "likely_erpnext_doctypes": ["Sales Order", "Project"]},
            {"filename": "raw_purchase_orders.csv", "likely_erpnext_doctypes": ["Purchase Order", "Item"]},
        ],
    }


def _report():
    manifest = build_manifest_v2(THIRD_RUN_FILES, created_at="2026-06-05T00:00:00Z")
    manifest["corpus_understanding"] = _corpus()
    files = manifest.get("files") or THIRD_RUN_FILES
    inputs = build_map_validate_inputs(
        project_id="test",
        files=files if isinstance(files, dict) and all(isinstance(v, str) for v in files.values()) else THIRD_RUN_FILES,
        target_structure=TARGET,
        corpus_understanding=_corpus(),
        company_context={"company_name": "Green Surface"},
    )
    return assess_map_validate_offline(inputs)


def test_offline_maps_core_doctypes():
    report = _report()
    mapped = set(report.mapped_doctypes)
    assert "Customer" in mapped
    assert "Supplier" in mapped
    assert "Sales Order" in mapped
    assert "Purchase Order" in mapped


def test_offline_validation_not_fail():
    report = _report()
    assert report.validation_level in ("pass", "partial")
    passed_maps = [r for r in report.map_results if r.passed]
    assert len(passed_maps) >= 4


def test_validate_ui_payload_shape():
    from containers.implementation.map_validate.validate_ui import build_validate_ui_from_report

    report = _report()
    ui = build_validate_ui_from_report(report)
    assert ui["validation_level"] in ("pass", "partial", "fail")
    assert "executive_summary" in ui
    assert "map_results" in ui
