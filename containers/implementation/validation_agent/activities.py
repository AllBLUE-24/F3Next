"""
Validation Agent — Temporal activities for pre-import data validation.

v2: Reads from ISTargetStructure + ISMappedData.
    Writes ISValidationResult + ISValidationError rows.
    Returns "success" string.

Protocol: Validation rules (required fields, enum values) are read from
erpnext_doctype_graph.json and field_mappings.json. The old in-code dicts
are preserved as FALLBACK constants so existing behaviour is never broken.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "erpnext"
_GRAPH_PATH   = _KB_DIR / "erpnext_doctype_graph.json"
_FMAP_PATH    = _KB_DIR / "schema" / "field_mappings.json"


def _load_graph() -> Dict:
    """Load doctype graph; returns empty dict on any failure."""
    try:
        with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_field_mappings() -> Dict:
    """Load field mappings; returns empty dict on any failure."""
    try:
        with open(_FMAP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

import boto3
from botocore.config import Config
from temporalio import activity


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


# ── Embedded service logic ────────────────────────────────────────────────────

class _ValidationEngine:
    # ── FALLBACK constants (used when JSON graph/schema don't have the entry) ──
    # These preserve all existing behaviour. New doctypes only need graph entries.
    _REQUIRED_FIELDS_FALLBACK: Dict[str, List[str]] = {
        "Item":             ["item_code", "item_name", "item_group", "stock_uom"],
        "Customer":         ["customer_name", "customer_group", "territory"],
        "Supplier":         ["supplier_name", "supplier_group"],
        "Employee":         ["employee_name", "date_of_joining"],
        "Sales Order":      ["customer", "transaction_date", "items"],
        "Sales Invoice":    ["customer", "posting_date"],
        "Purchase Invoice": ["supplier", "bill_no", "bill_date"],
        "Payment Entry":    ["payment_type", "party_type", "party", "paid_amount"],
        "Journal Entry":    ["posting_date", "accounts"],
    }

    _ENUM_FIELDS_FALLBACK: Dict[str, Dict[str, List[str]]] = {
        "Payment Entry": {
            "payment_type": ["Receive", "Pay", "Internal Transfer"],
            "party_type": ["Customer", "Supplier", "Employee"],
        },
        "Customer": {
            "customer_type": ["Company", "Individual"],
        },
        "Supplier": {
            "supplier_type": ["Company", "Individual"],
        },
        "Employee": {
            "status": ["Active", "Inactive", "Suspended", "Left"],
        },
    }

    def __init__(self, graph: Optional[Dict] = None, field_mappings: Optional[Dict] = None):
        self._graph = graph or {}
        self._field_mappings = field_mappings or {}

    def _get_required_fields(self, doctype: str) -> List[str]:
        """Read required_fields from graph; fall back to hardcoded list."""
        graph_fields = (
            self._graph.get("doctypes", {})
                       .get(doctype, {})
                       .get("required_fields", [])
        )
        if graph_fields:
            return graph_fields
        return self._REQUIRED_FIELDS_FALLBACK.get(doctype, [])

    def _get_enum_rules(self, doctype: str) -> Dict[str, List[str]]:
        """Read Select fields from field_mappings; fall back to hardcoded dict."""
        dt_fields = (
            self._field_mappings.get("doctypes", {})
                                .get(doctype, {})
                                .get("field_mappings", {})
        )
        enum_rules: Dict[str, List[str]] = {}
        for _fn, cfg in dt_fields.items():
            if cfg.get("fieldtype") == "Select" and cfg.get("options"):
                opts = [o.strip() for o in str(cfg["options"]).split("\n") if o.strip()]
                if opts:
                    enum_rules[cfg.get("fieldname", _fn)] = opts
        if enum_rules:
            return enum_rules
        return self._ENUM_FIELDS_FALLBACK.get(doctype, {})

    def validate(self, mapped_data: Dict[str, Any], target_structure: Dict[str, Any]) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "overall": "pass",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": [],
            "errors": [],
            "warnings": [],
        }
        
        required_doctypes = target_structure.get("required_doctypes", [])
        rules = target_structure.get("validation_rules", {})

        for dt, data in mapped_data.items():
            check = self._check_doctype(dt, data, rules)
            report["checks"].append(check)
            if check["status"] == "fail":
                report["errors"].extend(check["errors"])
                report["overall"] = "fail"
            report["warnings"].extend(check["warnings"])

        # ── COVERAGE CHECK: are major doctypes missing from mapped data? ──
        if required_doctypes:
            mapped_doctypes = set(mapped_data.keys())
            # Core master data doctypes that should ideally be present
            core_doctypes = {"Item", "Customer", "Supplier"}
            missing_core = core_doctypes.intersection(set(required_doctypes)) - mapped_doctypes
            if missing_core:
                report["warnings"].append(
                    f"Coverage gap: required doctypes not mapped: {sorted(missing_core)}"
                )
            all_missing = set(required_doctypes) - mapped_doctypes
            if len(all_missing) > len(required_doctypes) * 0.5:
                report["warnings"].append(
                    f"Only {len(mapped_doctypes)}/{len(required_doctypes)} required doctypes have mapped data"
                )

        return report

    def _check_doctype(self, doctype: str, data: Dict, rules: Dict) -> Dict:
        check: Dict[str, Any] = {"doctype": doctype, "status": "pass", "errors": [], "warnings": [], "row_count": 0}
        
        # Support both 'rows' (from earlier JSON structure) and 'records' (from fixed mapped payload)
        rows = data.get("records", data.get("rows", []))
        check["row_count"] = len(rows) if isinstance(rows, list) else 0

        # ── ROW COUNT SANITY ──
        if check["row_count"] == 0:
            check["warnings"].append(f"{doctype}: 0 records mapped — this doctype has no data")
        
        # ── FIELD COUNT SANITY ──
        if rows and isinstance(rows, list) and rows[0]:
            fields_per_record = len([k for k, v in rows[0].items() if v is not None and v != ""])
            if fields_per_record <= 1:
                check["warnings"].append(
                    f"{doctype}: records have only {fields_per_record} non-empty field(s) — critically sparse data"
                )

        # Required-field check
        required = self._get_required_fields(doctype)
        if rows and required:
            sample = rows[0]
            for field in required:
                if field not in sample and not any(field in str(k) for k in sample.keys()):
                    check["errors"].append(f"Missing required field: {field}")
                    check["status"] = "fail"

        # ── ENUM VALUE VALIDATION ──
        enum_rules = self._get_enum_rules(doctype)
        if rows and enum_rules:
            for i, row in enumerate(rows[:20]):
                for field_name, allowed_values in enum_rules.items():
                    val = row.get(field_name)
                    if val and str(val) not in allowed_values:
                        check["warnings"].append(
                            f"Row {i+1}: invalid enum value for '{field_name}': '{val}' "
                            f"(allowed: {allowed_values})"
                        )

        # Type sanity on first 10 rows
        for i, row in enumerate(rows[:10]):
            for k, v in row.items():
                if not v and v != 0:
                    continue
                if "date" in str(k).lower() and not self._is_date(str(v)):
                    check["warnings"].append(f"Row {i+1}: Invalid date format — {k}: {v}")
                if any(t in str(k).lower() for t in ("amount", "rate", "qty", "price")) and not self._is_numeric(str(v)):
                    check["warnings"].append(f"Row {i+1}: Non-numeric value — {k}: {v}")

        return check

    @staticmethod
    def _is_date(s: str) -> bool:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                datetime.strptime(s[:10], fmt)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _is_numeric(s: str) -> bool:
        return bool(re.match(r"^-?\d+\.?\d*$", s.replace(",", "").strip()))


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class ValidateInput:
    session_id: str
    project_id: str
    company_slug: str = "unknown"


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="validate_mapped_data")
async def validate_mapped_data(inp: ValidateInput) -> str:
    activity.logger.info("▶ validate_mapped_data started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import (
        ISSession, ISTargetStructure, ISMappedData,
        ISValidationResult, ISValidationError,
    )
    from sqlalchemy import select, update

    # ── 1. Read target_structure from is_target_structures ───────────────────
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISTargetStructure)
            .where(ISTargetStructure.session_id == uuid.UUID(inp.session_id))
            .order_by(ISTargetStructure.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        target_row = result.scalar_one_or_none()

        target_structure = {
            "required_doctypes": target_row.required_doctypes if target_row else [],
            "validation_rules": target_row.validation_rules if target_row else {},
        }

        # Get all mapped data for this session
        stmt = select(ISMappedData).where(ISMappedData.session_id == uuid.UUID(inp.session_id))
        result = await session.execute(stmt)
        mapped_data_rows = result.scalars().all()

    activity.logger.info("  Found %d mapped_data rows to validate", len(mapped_data_rows))

    # ── 2. Download extracted rows from R2 for each mapped_data ──────────────
    s3 = _get_s3_client()
    mapped_data: Dict[str, Any] = {}
    mapped_data_map: Dict[str, Any] = {}  # doctype → ISMappedData row

    for md_row in mapped_data_rows:
        doctype = md_row.target_doctype
        # We must validate the MAPPED payload, not the raw extracted rows
        r2_key = md_row.mapped_payload_r2_path

        if not r2_key:
            activity.logger.warning("  ⚠️ No mapped payload R2 key for %s, skipping", doctype)
            continue

        try:
            response = s3.get_object(Bucket="clean-data", Key=r2_key)
            payload_json = json.loads(response["Body"].read().decode("utf-8"))
            mapped_data[doctype] = payload_json
            mapped_data_map[doctype] = md_row
            activity.logger.info("  ✅ Loaded payload for %s from R2", doctype)
        except Exception as e:
            activity.logger.error("  ❌ Failed to load payload for %s: %s", doctype, e)

    # ── 3. Run validation engine ─────────────────────────────────────────────
    start_time = datetime.now()
    # Load context files so engine can read required_fields + enum rules from JSON
    engine = _ValidationEngine(graph=_load_graph(), field_mappings=_load_field_mappings())
    report = engine.validate(mapped_data, target_structure)
    duration = (datetime.now() - start_time).total_seconds()
    
    v_status = report.get("overall", "pass")
    n_errors = len(report.get("errors", []))
    n_warnings = len(report.get("warnings", []))
    activity.logger.info("  Validation result: %s | %d errors, %d warnings", v_status, n_errors, n_warnings)

    # ── 4. Upload validation report to R2 ────────────────────────────────────
    slug = inp.company_slug or "unknown"
    report_key = f"{slug}/{inp.project_id}/_validation/report.json"
    try:
        s3.put_object(
            Bucket="clean-data",
            Key=report_key,
            Body=json.dumps(report, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", report_key)
    except Exception as e:
        activity.logger.error("  ❌ R2 report upload failed: %s", e)

    # ── 5. Write ISValidationResult + ISValidationError + update ISMappedData
    try:
        async with AsyncSessionLocal() as session:
            for check in report.get("checks", []):
                doctype = check.get("doctype", "")
                md_row = mapped_data_map.get(doctype)
                
                # We need a mapped_data_id to link the result to the payload
                mapped_data_id = md_row.id if md_row else None
                
                if not mapped_data_id:
                    activity.logger.warning("  ⚠️ Cannot write validation result for %s (no mapped_data_id)", doctype)
                    continue

                # Create ISValidationResult
                result_id = uuid.uuid4()
                session.add(ISValidationResult(
                    id=result_id,
                    session_id=uuid.UUID(inp.session_id),
                    mapped_data_id=mapped_data_id,
                    doctype=doctype,
                    overall_status=check["status"],
                    report_r2_path=report_key,
                    total_errors=len(check.get("errors", [])),
                    total_warnings=len(check.get("warnings", [])),
                    total_records_checked=check.get("row_count", 0)
                ))

                # Flush the parent row into the transaction BEFORE adding children.
                # Without this, Postgres rejects the ISValidationError FKs because
                # the parent ISValidationResult row hasn't been sent to the DB yet.
                await session.flush()

                # Create ISValidationError rows for each error
                for err_msg in check.get("errors", []):
                    session.add(ISValidationError(
                        id=uuid.uuid4(),
                        validation_result_id=result_id,
                        doctype=doctype,
                        error_type="missing_required" if "Missing required" in err_msg else "business_rule",
                        error_message=err_msg,
                        severity="error",
                    ))

                # Create ISValidationError rows for each warning
                for warn_msg in check.get("warnings", []):
                    session.add(ISValidationError(
                        id=uuid.uuid4(),
                        validation_result_id=result_id,
                        doctype=doctype,
                        error_type="invalid_format" if "format" in warn_msg.lower() else "data_warning",
                        error_message=warn_msg,
                        severity="warning",
                    ))

                # Update ISMappedData.validation_status
                await session.execute(
                    update(ISMappedData)
                    .where(ISMappedData.id == mapped_data_id)
                    .values(validation_status="passed" if check["status"] == "pass" else "failed")
                )

            # Update session status
            await session.execute(
                update(ISSession)
                .where(ISSession.id == uuid.UUID(inp.session_id))
                .values(status="awaiting_validation_submission")
            )
            await session.commit()
            activity.logger.info("  ✅ Supabase updated | validation results + session status")
            
    except Exception as e:
        activity.logger.error("  ❌ Supabase DB write failed during validation: %s", e)

    # ── 6. Audit trail ───────────────────────────────────────────────────────
    try:
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="validation_run",
            actor="system",
            entity_type="validation",
            details={"overall": v_status, "errors": n_errors, "doctypes_checked": len(report.get("checks", []))},
            result="success",
        )
    except Exception as e:
         activity.logger.error("  ❌ Audit log failed: %s", e)

    activity.logger.info("✅ validate_mapped_data done | overall=%s errors=%d", v_status, n_errors)
    return v_status