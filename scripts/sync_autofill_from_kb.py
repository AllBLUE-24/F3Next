#!/usr/bin/env python3
"""
Sync workflow_gates.ERP_AUTOFILL_FIELDS from os_validation.json (Temporal sandbox).

Usage:
  python scripts/sync_autofill_from_kb.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_PATH = ROOT / "containers" / "knowledge_base" / "erpnext" / "schema" / "shared" / "os_validation.json"
GATES_PATH = ROOT / "containers" / "os" / "os_workflow" / "workflow_gates.py"

_BLOCK_RE = re.compile(
    r"(ERP_AUTOFILL_FIELDS: frozenset\[str\] = frozenset\(\{)(.*?)(\}\))",
    re.DOTALL,
)


def _load_kb_fields() -> list[str]:
    with open(KB_PATH, encoding="utf-8") as f:
        data = json.load(f)
    fields = data.get("erp_autofill_fields") or []
    return sorted({str(x).strip() for x in fields if str(x).strip()})


def _render_block(fields: list[str]) -> str:
    lines = ",\n".join(f'    "{f}"' for f in fields)
    return f"ERP_AUTOFILL_FIELDS: frozenset[str] = frozenset({{\n{lines},\n}})"


def sync(*, check_only: bool = False) -> int:
    fields = _load_kb_fields()
    expected_block = _render_block(fields)

    text = GATES_PATH.read_text(encoding="utf-8")
    m = _BLOCK_RE.search(text)
    if not m:
        print("Could not find ERP_AUTOFILL_FIELDS block in workflow_gates.py", file=sys.stderr)
        return 1

    current_inner = m.group(2)
    current_fields = sorted(
        x.strip().strip('"').strip("'")
        for x in re.findall(r'"([^"]+)"', current_inner)
    )

    if current_fields == fields:
        print("ERP_AUTOFILL_FIELDS already matches KB")
        return 0

    if check_only:
        print("Drift detected between KB and workflow_gates.py", file=sys.stderr)
        print(f"  KB:     {fields}", file=sys.stderr)
        print(f"  gates:  {current_fields}", file=sys.stderr)
        return 1

    new_text = _BLOCK_RE.sub(expected_block, text, count=1)
    GATES_PATH.write_text(new_text, encoding="utf-8")
    print(f"Updated {GATES_PATH.relative_to(ROOT)} ({len(fields)} fields)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Exit 1 if drift detected")
    args = parser.parse_args()
    raise SystemExit(sync(check_only=args.check))


if __name__ == "__main__":
    main()
