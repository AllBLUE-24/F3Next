"""
Shared manifest parsing utilities for Step 2 corpus pipeline.

Manifest v2 shape (backward-compatible with v1):
  {
    "_manifest_version": 2,
    "_created_at": "...",
    "file_count": N,
    "files": { "filename.csv": "<raw content>" },
    "file_meta": { ... },
    "corpus_understanding": { ... }
  }
"""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Dict, List, Optional, Tuple

MANIFEST_VERSION = 2
STRUCTURED_EXTENSIONS = {".csv", ".tsv", ".json"}
MAX_SAMPLE_ROWS = 3


def get_file_extension(filename: str) -> str:
    dot = filename.rfind(".")
    if dot == -1:
        return ""
    return filename[dot:].lower()


def parse_structured_content(content: str, filename: str) -> Dict[str, Any]:
    """Extract columns, row count, and sample rows from parseable file content."""
    ext = get_file_extension(filename)
    char_len = len(content or "")

    if not content or not content.strip():
        return {
            "columns": [],
            "row_count": 0,
            "sample_rows": [],
            "is_structured": False,
            "format": ext.lstrip(".") or "text",
            "char_len": char_len,
        }

    if ext in (".csv", ".tsv"):
        delimiter = "\t" if ext == ".tsv" else ","
        try:
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            rows = list(reader)
            columns = [c for c in (reader.fieldnames or []) if c]
            sample_rows = [_stringify_row(r) for r in rows[:MAX_SAMPLE_ROWS]]
            return {
                "columns": columns,
                "row_count": len(rows),
                "sample_rows": sample_rows,
                "is_structured": bool(columns),
                "format": ext.lstrip("."),
                "char_len": char_len,
            }
        except Exception:
            pass

    if ext == ".json":
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                columns = list(parsed[0].keys())
                sample_rows = [_stringify_row(r) for r in parsed[:MAX_SAMPLE_ROWS]]
                return {
                    "columns": columns,
                    "row_count": len(parsed),
                    "sample_rows": sample_rows,
                    "is_structured": True,
                    "format": "json",
                    "char_len": char_len,
                }
            if isinstance(parsed, dict):
                for key in ("rows", "data", "records", "items"):
                    rows = parsed.get(key)
                    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                        columns = list(rows[0].keys())
                        sample_rows = [_stringify_row(r) for r in rows[:MAX_SAMPLE_ROWS]]
                        return {
                            "columns": columns,
                            "row_count": len(rows),
                            "sample_rows": sample_rows,
                            "is_structured": True,
                            "format": "json",
                            "char_len": char_len,
                        }
        except Exception:
            pass

    line_count = content.count("\n") + (1 if content.strip() else 0)
    return {
        "columns": [],
        "row_count": max(line_count - 1, 0),
        "sample_rows": [],
        "is_structured": False,
        "format": ext.lstrip(".") or "text",
        "char_len": char_len,
    }


def _stringify_row(row: Dict[str, Any]) -> Dict[str, str]:
    return {str(k): "" if v is None else str(v) for k, v in row.items()}


def build_file_meta(contents: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Build per-file metadata for all entries in a raw-content map."""
    meta: Dict[str, Dict[str, Any]] = {}
    for fname, content in contents.items():
        parsed = parse_structured_content(content, fname)
        parsed["source_file"] = fname
        meta[fname] = parsed
    return meta


def normalize_manifest_input(
    manifest_or_files: Dict[str, Any],
) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Accept either a full v2 manifest or a legacy v1 {filename: content} map.

    Returns: (files, file_meta, corpus_understanding)
    """
    if not manifest_or_files:
        return {}, {}, None

    if "files" in manifest_or_files and isinstance(manifest_or_files["files"], dict):
        files = {
            k: v for k, v in manifest_or_files["files"].items()
            if isinstance(v, str)
        }
        file_meta = manifest_or_files.get("file_meta") or {}
        if not file_meta and files:
            file_meta = build_file_meta(files)
        corpus = manifest_or_files.get("corpus_understanding")
        return files, file_meta, corpus

    if all(isinstance(v, str) for v in manifest_or_files.values()):
        files = dict(manifest_or_files)
        return files, build_file_meta(files), None

    return {}, {}, None


def extract_files_from_manifest(manifest: Dict[str, Any]) -> Dict[str, str]:
    """Backward-compatible helper: return {filename: content} from any manifest shape."""
    files, _, _ = normalize_manifest_input(manifest)
    return files


def build_manifest_v2(contents: Dict[str, str], *, created_at: str) -> Dict[str, Any]:
    """Assemble a v2 manifest dict from raw file contents."""
    file_meta = build_file_meta(contents)
    return {
        "_manifest_version": MANIFEST_VERSION,
        "_created_at": created_at,
        "file_count": len(contents),
        "files": contents,
        "file_meta": file_meta,
    }


def corpus_file_understanding(
    corpus_understanding: Optional[Dict[str, Any]],
    filename: str,
) -> Optional[Dict[str, Any]]:
    """Return per-file corpus understanding entry, if present."""
    if not corpus_understanding:
        return None
    files = corpus_understanding.get("files") or []
    if isinstance(files, dict):
        return files.get(filename)
    for entry in files:
        if isinstance(entry, dict) and entry.get("filename") == filename:
            return entry
    return None


def corpus_exclusions_by_doctype(corpus_understanding: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Map ERPNext doctype → list of filenames that explicitly say they are NOT that doctype.
    Used by gap_analyzer to suppress false-positive column matches.
    """
    if not corpus_understanding:
        return {}

    exclusions: Dict[str, List[str]] = {}
    files = corpus_understanding.get("files") or []
    if isinstance(files, dict):
        iterable = [{"filename": k, **v} for k, v in files.items()]
    else:
        iterable = files

    for entry in iterable:
        if not isinstance(entry, dict):
            continue
        fname = entry.get("filename") or entry.get("source_file") or ""
        for dt in entry.get("explicitly_not_doctypes") or []:
            dt_name = str(dt or "").strip()
            if dt_name and fname:
                exclusions.setdefault(dt_name, []).append(fname)
    return exclusions
