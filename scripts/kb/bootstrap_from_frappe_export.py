#!/usr/bin/env python3
"""
Bootstrap modular KB mapping/*.json files from a Frappe bench export.

Input: attachments/kb_bootstrap_export.json (dict of doctype -> export payload)
Output: containers/knowledge_base/erpnext/schema/mapping/{Doctype}.json

Usage:
  python scripts/kb/bootstrap_from_frappe_export.py
  python scripts/kb/bootstrap_from_frappe_export.py --dry-run
  python scripts/kb/bootstrap_from_frappe_export.py --doctype "Purchase Receipt"
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "attachments" / "kb_bootstrap_export.json"
DEFAULT_OUTPUT = REPO_ROOT / "containers" / "knowledge_base" / "erpnext" / "schema" / "mapping"

SKIP_EXACT: Set[str] = {
    "DocType",
    "Module Def",
    "Patch Log",
    "Patch",
    "Scheduled Job Type",
    "Version",
    "Access Log",
    "Error Log",
    "Activity Log",
    "Comment",
    "File",
    "Communication",
    "Email Queue",
    "Notification Log",
}

SKIP_CONTAINS: tuple[str, ...] = (
    " Settings",
    "Ledger Entry",
    "Repost Accounting",
    "Process Statement Of Accounts",
    "Closing Stock Balance",
    "Transaction Deletion Record",
    "Prepared Report",
    "Auto Email Report",
)

SKIP_MODULES: Set[str] = {
    "Automation",
    "Integrations",
    "Email",
    "Social",
    "Desk",
}


def _synonyms(fieldname: str, label: str) -> List[str]:
    fn = str(fieldname or "").strip()
    lb = str(label or "").strip()
    out = {
        fn,
        fn.lower(),
        fn.replace("_", " "),
        lb,
        lb.lower(),
        lb.lower().replace(" ", "_"),
    }
    return [s for s in out if s and len(s) >= 2]


def _should_skip(doctype: str, module: str) -> bool:
    if doctype in SKIP_EXACT:
        return True
    for frag in SKIP_CONTAINS:
        if frag in doctype:
            return True
    if module in SKIP_MODULES:
        return True
    if doctype.startswith("Report") or doctype.endswith(" Report"):
        return True
    return False


def _merge_field(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(incoming)
    if not existing:
        return out
    old_syns = list(existing.get("user_input_synonyms") or [])
    new_syns = list(out.get("user_input_synonyms") or [])
    merged = list(dict.fromkeys(old_syns + new_syns))
    if merged:
        out["user_input_synonyms"] = merged
    for key in ("note", "validation", "common_values", "default_value", "naming_series"):
        if existing.get(key) not in (None, "") and out.get(key) in (None, "", []):
            out[key] = existing[key]
    if existing.get("mandatory") and not out.get("mandatory"):
        out["mandatory"] = True
    return out


def _convert_child_fields(child_export: Dict[str, Any]) -> Dict[str, Any]:
    child_fields: Dict[str, Any] = {}
    for fname, cfg in (child_export.get("field_mappings") or {}).items():
        if cfg.get("fieldtype") == "Table":
            continue
        entry = dict(cfg)
        entry.setdefault("fieldname", fname)
        entry["user_input_synonyms"] = _synonyms(fname, cfg.get("label") or fname)
        child_fields[fname] = entry
    return child_fields


def _convert_export(doctype: str, export: Dict[str, Any]) -> Dict[str, Any]:
    field_mappings: Dict[str, Any] = {}
    child_tables = export.get("child_tables") or {}

    for fname, cfg in (export.get("field_mappings") or {}).items():
        if cfg.get("fieldtype") == "Table":
            child_name = cfg.get("options")
            child_export = child_tables.get(fname) or (child_tables.get(child_name) if child_name else None)
            entry = {
                "fieldname": fname,
                "fieldtype": "Table",
                "options": child_name,
                "mandatory": bool(cfg.get("mandatory")),
                "child_doctype": child_name,
                "user_input_synonyms": _synonyms(fname, cfg.get("label") or fname),
            }
            if isinstance(child_export, dict):
                entry["child_fields"] = _convert_child_fields(child_export)
            field_mappings[fname] = entry
            continue

        entry = dict(cfg)
        entry.setdefault("fieldname", fname)
        entry["user_input_synonyms"] = _synonyms(fname, cfg.get("label") or fname)
        if entry.get("fieldtype") == "Select" and isinstance(entry.get("options"), list):
            pass  # keep list form used by existing KB
        field_mappings[fname] = entry

    hints = [
        doctype.lower(),
        doctype.lower().replace(" ", "_"),
    ]
    autoname = export.get("autoname") or ""
    if "naming_series:" in str(autoname):
        hints.append("naming_series")

    out: Dict[str, Any] = {
        "doctype_name": doctype,
        "mandatory_fields": list(export.get("mandatory_fields") or []),
        "doctype_classifier_hints": sorted(set(h for h in hints if h)),
        "field_mappings": field_mappings,
    }
    if export.get("is_submittable"):
        out["is_submittable"] = True
    return out


def _mapping_path(output_dir: Path, doctype: str) -> Path:
    return output_dir / f"{doctype}.json"


def bootstrap(
    *,
    input_path: Path,
    output_dir: Path,
    dry_run: bool = False,
    only_doctype: Optional[str] = None,
) -> Dict[str, int]:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Export must be a JSON object keyed by doctype name")

    stats = {"written": 0, "skipped": 0, "merged": 0, "errors": 0}

    for doctype, export in sorted(raw.items()):
        if only_doctype and doctype != only_doctype:
            continue
        if not isinstance(export, dict):
            stats["errors"] += 1
            continue
        module = str(export.get("module") or "")
        if _should_skip(doctype, module):
            stats["skipped"] += 1
            continue
        if export.get("error"):
            stats["skipped"] += 1
            continue

        try:
            converted = _convert_export(doctype, export)
        except Exception:
            stats["errors"] += 1
            continue

        path = _mapping_path(output_dir, doctype)
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
            if existing.get("naming_series") and not converted.get("naming_series"):
                converted["naming_series"] = existing["naming_series"]
            if existing.get("doctype_classifier_hints"):
                converted["doctype_classifier_hints"] = sorted(set(
                    (existing.get("doctype_classifier_hints") or [])
                    + (converted.get("doctype_classifier_hints") or [])
                ))
            merged_fields: Dict[str, Any] = {}
            old_fmap = existing.get("field_mappings") or {}
            for fname, cfg in converted.get("field_mappings", {}).items():
                merged_fields[fname] = _merge_field(old_fmap.get(fname) or {}, cfg)
            for fname, cfg in old_fmap.items():
                if fname not in merged_fields:
                    merged_fields[fname] = cfg
            converted["field_mappings"] = merged_fields
            stats["merged"] += 1
        else:
            stats["written"] += 1

        if dry_run:
            continue

        output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(converted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap ERPNext mapping KB from Frappe export")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--doctype", type=str, default=None)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    stats = bootstrap(
        input_path=args.input,
        output_dir=args.output,
        dry_run=args.dry_run,
        only_doctype=args.doctype,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
