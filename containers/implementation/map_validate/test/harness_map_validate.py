"""Offline harness for Step 4 map & validate."""
from __future__ import annotations

import argparse
import json
import sys

from containers.implementation.file_io.manifest_utils import build_manifest_v2
from containers.implementation.map_validate.assess import assess_map_validate_offline
from containers.implementation.map_validate.inputs import build_map_validate_inputs

THIRD_RUN_FILES = {
    "messy_partners.csv": (
        "Company_Name,Role,City,Contact\r\n"
        "Rohan Construction,Customer,Mumbai,Rohan\r\n"
        "Gupta Chemical Traders,Supplier,Ahmedabad,S.K. Gupta\r\n"
    ),
    "client_orders.csv": (
        "Client,Project,Target_Date,Product,Vol,Price\r\n"
        "Rohan Construction,PRJ-Mumbai-Mall,2026-08-15,SRV-INSTALL,12000,\r\n"
    ),
    "raw_purchase_orders.csv": (
        "PO_Number,Vendor_Name,Item,Ordered_Qty,Price_Per_Unit\r\n"
        "PO-26-001,Gupta Chemical Traders,RM-EPOX-LIQ,2000,4.60\r\n"
    ),
}

TARGET = {
    "seed_doctypes": ["Customer", "Supplier", "Sales Order", "Purchase Order", "Item"],
    "required_doctypes": ["Customer", "Supplier", "Sales Order", "Purchase Order"],
}


def _fixture():
    manifest = build_manifest_v2(THIRD_RUN_FILES, created_at="2026-06-05T00:00:00Z")
    corpus = {
        "files": [
            {"filename": "messy_partners.csv", "likely_erpnext_doctypes": ["Customer", "Supplier"]},
            {"filename": "client_orders.csv", "likely_erpnext_doctypes": ["Sales Order"]},
            {"filename": "raw_purchase_orders.csv", "likely_erpnext_doctypes": ["Purchase Order"]},
        ],
    }
    files = manifest.get("files") or THIRD_RUN_FILES
    return build_map_validate_inputs(
        project_id="harness",
        files=files,
        target_structure=TARGET,
        corpus_understanding=corpus,
    )


def run_matrix() -> int:
    report = assess_map_validate_offline(_fixture())
    passed = sum(1 for r in report.map_results if r.passed)
    print(json.dumps({
        "validation_level": report.validation_level,
        "import_ready": report.import_ready,
        "mapped_doctypes": report.mapped_doctypes,
        "map_pass_count": passed,
        "error_count": report.error_count,
        "executive_summary": report.executive_summary,
    }, indent=2))
    if report.validation_level == "fail":
        return 1
    if passed < 3:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Step 4 map_validate harness")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--fixture", type=str)
    args = parser.parse_args()
    if args.matrix or args.fixture == "green_surface_3rd_run":
        return run_matrix()
    if args.fixture:
        print(f"Unknown fixture: {args.fixture}", file=sys.stderr)
        return 2
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
