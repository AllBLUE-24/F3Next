"""Offline harness for Step 3 readiness."""
from __future__ import annotations

import argparse
import json
import sys

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

TARGET = {
    "seed_doctypes": [
        "Project", "Item", "Stock Entry", "Purchase Order", "Sales Order",
        "Item Variant", "Task", "Timesheet", "Quotation", "Delivery Note",
    ],
    "deferred_doctypes": ["Batch", "BOM", "Work Order", "Job Card"],
}


def _fixture_manifest():
    manifest = build_manifest_v2(THIRD_RUN_FILES, created_at="2026-06-05T00:00:00Z")
    manifest["corpus_understanding"] = {
        "files": [
            {"filename": "messy_partners.csv", "likely_erpnext_doctypes": ["Customer", "Supplier"]},
            {"filename": "client_orders.csv", "likely_erpnext_doctypes": ["Sales Order", "Project", "Customer"]},
            {"filename": "raw_purchase_orders.csv", "likely_erpnext_doctypes": ["Purchase Order", "Supplier", "Item"]},
        ],
    }
    return manifest


def run_matrix() -> int:
    inputs = build_readiness_inputs(
        project_id="harness",
        manifest=_fixture_manifest(),
        target_structure=TARGET,
    )
    report = assess_readiness(inputs)
    ready = len(report.ready_doctypes)
    rows = len(report.matrix.rows)
    print(json.dumps({
        "readiness_level": report.readiness_level,
        "ready_doctypes": ready,
        "matrix_rows": rows,
        "blocking_gaps": sum(1 for g in report.gap_items if g.get("severity") == "blocking"),
        "minimum_viable_possible": report.minimum_viable_import_possible,
        "executive_summary": report.executive_summary,
    }, indent=2))
    if rows < 5:
        return 1
    if ready < 6:
        return 1
    return 0


def run_fixture(name: str) -> int:
    if name != "green_surface_3rd_run":
        print(f"Unknown fixture: {name}", file=sys.stderr)
        return 2
    return run_matrix()


def main() -> int:
    parser = argparse.ArgumentParser(description="Step 3 readiness harness")
    parser.add_argument("--matrix", action="store_true", help="Run offline matrix golden")
    parser.add_argument("--fixture", type=str, help="Run named fixture")
    args = parser.parse_args()
    if args.matrix or args.fixture:
        if args.fixture:
            return run_fixture(args.fixture)
        return run_matrix()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
