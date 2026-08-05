"""Offline harness for Step 5 phased import."""
from __future__ import annotations

import argparse
import json
import sys

from containers.implementation.import_exec.test.test_offline_3rd_run import _import_report


def run_matrix() -> int:
    report = _import_report()
    create_doctypes = sorted(
        {s.doctype for s in report.steps if s.action == "create" and s.records > 0}
    )
    print(json.dumps({
        "plan_status": report.plan_status,
        "import_level": report.import_level,
        "import_ready": report.import_ready,
        "create_step_count": report.create_step_count,
        "data_gap_count": report.data_gap_count,
        "create_doctypes": create_doctypes,
        "ordered_phase_ids": report.ordered_phase_ids,
        "executive_summary": report.executive_summary,
    }, indent=2))

    if report.plan_status == "blocked":
        return 1
    required = {"Customer", "Supplier", "Sales Order", "Purchase Order"}
    if not required.issubset(set(create_doctypes)):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Step 5 import harness")
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
