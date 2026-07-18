"""
Step 2 v1 gate checkers — deterministic pass/fail for manifest + corpus understanding.

Used by harness and unit tests. No KB patch files; validates shape and minimum quality.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from containers.implementation.corpus.manifest import MANIFEST_VERSION, extract_files_from_manifest
from containers.implementation.corpus.schemas import CorpusUnderstanding
from containers.implementation.corpus.validation import validate_corpus_understanding

REQUIRED_MANIFEST_KEYS = ("_manifest_version", "_created_at", "file_count", "files", "file_meta")
GOLDEN_MIN_CONFIDENCE = 0.45


@dataclass
class CheckerIssue:
    code: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class Step2GateResult:
    passed: bool
    manifest_ok: bool
    understanding_ok: bool
    status: str  # ok | partial | failed | skipped
    issues: List[CheckerIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[CheckerIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[CheckerIssue]:
        return [i for i in self.issues if i.severity == "warning"]


def check_manifest_v2_shape(manifest: Dict[str, Any]) -> List[CheckerIssue]:
    """Validate manifest v2 structural contract."""
    issues: List[CheckerIssue] = []

    if not manifest:
        return [CheckerIssue("EMPTY_MANIFEST", "Manifest is empty", "error")]

    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            issues.append(CheckerIssue("MISSING_MANIFEST_KEY", f"Missing key: {key}", "error"))

    version = manifest.get("_manifest_version")
    if version is not None and version != MANIFEST_VERSION:
        issues.append(CheckerIssue(
            "BAD_MANIFEST_VERSION",
            f"Expected _manifest_version={MANIFEST_VERSION}, got {version}",
            "error",
        ))

    files = manifest.get("files") or {}
    file_meta = manifest.get("file_meta") or {}
    if not isinstance(files, dict) or not files:
        issues.append(CheckerIssue("NO_FILES", "Manifest has no parsed files", "error"))
    elif len(files) != manifest.get("file_count", len(files)):
        issues.append(CheckerIssue(
            "FILE_COUNT_MISMATCH",
            f"file_count={manifest.get('file_count')} but files has {len(files)} entries",
            "warning",
        ))

    for fname in files:
        if fname not in file_meta:
            issues.append(CheckerIssue(
                "MISSING_FILE_META",
                f"No file_meta for {fname}",
                "error",
            ))
            continue
        meta = file_meta[fname]
        if meta.get("is_structured") and not meta.get("columns"):
            issues.append(CheckerIssue(
                "STRUCTURED_WITHOUT_COLUMNS",
                f"{fname}: is_structured=true but columns empty",
                "warning",
            ))

    return issues


def check_corpus_understanding_shape(
    corpus: Optional[Dict[str, Any]],
    expected_filenames: Sequence[str],
    *,
    require_understanding: bool = True,
) -> List[CheckerIssue]:
    """Validate corpus_understanding block on a manifest."""
    issues: List[CheckerIssue] = []

    if not corpus:
        if require_understanding:
            issues.append(CheckerIssue(
                "NO_CORPUS_UNDERSTANDING",
                "Manifest missing corpus_understanding",
                "error",
            ))
        return issues

    if not (corpus.get("corpus_summary") or "").strip():
        issues.append(CheckerIssue("EMPTY_CORPUS_SUMMARY", "corpus_summary is empty", "error"))

    files = corpus.get("files") or []
    if not files:
        issues.append(CheckerIssue("NO_FILE_UNDERSTANDING", "corpus_understanding.files is empty", "error"))
        return issues

    if isinstance(files, dict):
        entries = [{"filename": k, **v} for k, v in files.items()]
    else:
        entries = list(files)

    returned = {e.get("filename") for e in entries if isinstance(e, dict)}
    for fname in expected_filenames:
        if fname not in returned:
            issues.append(CheckerIssue(
                "MISSING_FILE_UNDERSTANDING",
                f"No understanding entry for {fname}",
                "error",
            ))

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        fname = entry.get("filename") or "?"
        if not (entry.get("business_description") or "").strip():
            issues.append(CheckerIssue(
                "EMPTY_BUSINESS_DESCRIPTION",
                f"{fname}: business_description empty",
                "error",
            ))
        confidence = float(entry.get("confidence") or 0)
        if confidence < GOLDEN_MIN_CONFIDENCE:
            issues.append(CheckerIssue(
                "LOW_CONFIDENCE",
                f"{fname}: confidence {confidence:.2f} below {GOLDEN_MIN_CONFIDENCE}",
                "warning",
            ))

    return issues


def check_golden_expectations(
    corpus: Dict[str, Any],
    *,
    file_doctype_expectations: Optional[Dict[str, List[str]]] = None,
    file_exclusion_expectations: Optional[Dict[str, List[str]]] = None,
) -> List[CheckerIssue]:
    """Optional golden matrix assertions for a fixture."""
    issues: List[CheckerIssue] = []
    files = corpus.get("files") or []
    if isinstance(files, dict):
        by_name = files
    else:
        by_name = {e.get("filename"): e for e in files if isinstance(e, dict)}

    for fname, expected_doctypes in (file_doctype_expectations or {}).items():
        entry = by_name.get(fname) or {}
        actual = set(entry.get("likely_erpnext_doctypes") or [])
        for dt in expected_doctypes:
            if dt not in actual:
                issues.append(CheckerIssue(
                    "GOLDEN_DOCTYPE_MISS",
                    f"{fname}: expected doctype {dt}, got {sorted(actual)}",
                    "error",
                ))

    for fname, excluded in (file_exclusion_expectations or {}).items():
        entry = by_name.get(fname) or {}
        actual_excl = set(entry.get("explicitly_not_doctypes") or [])
        for dt in excluded:
            if dt not in actual_excl:
                issues.append(CheckerIssue(
                    "GOLDEN_EXCLUSION_MISS",
                    f"{fname}: expected exclusion {dt}, got {sorted(actual_excl)}",
                    "error",
                ))

    return issues


def evaluate_step2_gate(
    manifest: Dict[str, Any],
    *,
    require_understanding: bool = True,
    file_doctype_expectations: Optional[Dict[str, List[str]]] = None,
    file_exclusion_expectations: Optional[Dict[str, List[str]]] = None,
) -> Step2GateResult:
    """
    Run all Step 2 checkers and return a single gate result.

    passed=True when no error-severity issues and status is ok or partial.
    """
    issues: List[CheckerIssue] = []
    issues.extend(check_manifest_v2_shape(manifest))

    expected = list(extract_files_from_manifest(manifest).keys())
    corpus = manifest.get("corpus_understanding")
    issues.extend(check_corpus_understanding_shape(
        corpus, expected, require_understanding=require_understanding,
    ))

    if corpus and (file_doctype_expectations or file_exclusion_expectations):
        issues.extend(check_golden_expectations(
            corpus,
            file_doctype_expectations=file_doctype_expectations,
            file_exclusion_expectations=file_exclusion_expectations,
        ))

    validation_status = "skipped"
    if corpus and expected:
        try:
            understanding = CorpusUnderstanding.model_validate(corpus)
            validation_status, val_warnings = validate_corpus_understanding(understanding, expected)
            for w in val_warnings:
                sev = "error" if w.get("code") == "EMPTY_OUTPUT" else "warning"
                issues.append(CheckerIssue(w["code"], w["message"], sev))
        except Exception as exc:
            issues.append(CheckerIssue("INVALID_CORPUS_SCHEMA", str(exc), "error"))
            validation_status = "failed"

    manifest_ok = not any(i.severity == "error" for i in issues if i.code.startswith(("EMPTY_MANIFEST", "MISSING_MANIFEST", "NO_FILES", "MISSING_FILE_META")))
    understanding_errors = {
        "NO_CORPUS_UNDERSTANDING", "NO_FILE_UNDERSTANDING", "MISSING_FILE_UNDERSTANDING",
        "EMPTY_CORPUS_SUMMARY", "EMPTY_BUSINESS_DESCRIPTION", "INVALID_CORPUS_SCHEMA",
        "GOLDEN_DOCTYPE_MISS", "GOLDEN_EXCLUSION_MISS",
    }
    understanding_ok = not any(i.severity == "error" and i.code in understanding_errors for i in issues)

    if any(i.severity == "error" for i in issues):
        status = "failed"
    elif any(i.severity == "warning" for i in issues) or validation_status == "partial":
        status = "partial"
    elif validation_status == "ok":
        status = "ok"
    else:
        status = "skipped" if not require_understanding else validation_status

    passed = status in ("ok", "partial") and manifest_ok and (understanding_ok or not require_understanding)

    return Step2GateResult(
        passed=passed,
        manifest_ok=manifest_ok,
        understanding_ok=understanding_ok,
        status=status,
        issues=issues,
    )
