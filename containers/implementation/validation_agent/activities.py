"""
Validation Agent — Temporal activities for pre-import data validation.

v2: Reads from ISTargetStructure + ISMappedData (not ISSession/ISMapping).
    Writes ISValidationResult + ISValidationError rows.
    Returns "success" string.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    REQUIRED_FIELDS: Dict[str, List[str]] = {
        "Item":             ["item_code", "item_name", "item_group", "stock_uom"],
        "Customer":         ["customer_name", "customer_type", "customer_group", "territory"],
        "Supplier":         ["supplier_name", "supplier_type", "supplier_group"],
        "Sales Invoice":    ["customer", "posting_date"],
        "Purchase Invoice": ["supplier", "bill_no", "bill_date"],
    }

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
            if dt not in required_doctypes:
                continue
            check = self._check_doctype(dt, data, rules)
            report["checks"].append(check)
            if check["status"] == "fail":
                report["errors"].extend(check["errors"])
                report["overall"] = "fail"
            report["warnings"].extend(check["warnings"])

        return report

    def _check_doctype(self, doctype: str, data: Dict, rules: Dict) -> Dict:
        check: Dict[str, Any] = {"doctype": doctype, "status": "pass", "errors": [], "warnings": [], "row_count": 0}
        rows = data.get("rows", data.get("data", []))
        check["row_count"] = len(rows) if isinstance(rows, list) else 0

        # Required-field check
        required = self.REQUIRED_FIELDS.get(doctype, [])
        if rows and required:
            sample = rows[0]
            for field in required:
                if field not in sample and not any(field in str(k) for k in sample.keys()):
                    check["errors"].append(f"Missing required field: {field}")
                    check["status"] = "fail"

        # Type sanity on first 10 rows
        for i, row in enumerate(rows[:10]):
            for k, v in row.items():
                if not v and v != 0:
                    continue
                if "date" in k.lower() and not self._is_date(str(v)):
                    check["warnings"].append(f"Row {i+1}: Invalid date format — {k}: {v}")
                if any(t in k.lower() for t in ("amount", "rate", "qty", "price")) and not self._is_numeric(str(v)):
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
    """
    Run pre-import validation checks on mapped data.
    
    v2 schema:
      1. Reads target_structure from is_target_structures
      2. Reads mapped doctypes from is_mapped_data
      3. Downloads extracted rows from R2
      4. Runs validation
      5. Writes ISValidationResult + ISValidationError rows
      6. Updates ISMappedData.validation_status
      7. Updates is_sessions.status
    
    Returns: "success" or "fail" (based on validation outcome)
    """
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

        if not target_row:
            activity.logger.error("  ❌ No target structure found for session %s", inp.session_id)
            return "error:no_target_structure"

        target_structure = {
            "required_doctypes": target_row.required_doctypes or [],
            "validation_rules": target_row.validation_rules or {},
        }

        # Get all mapped data for this session
        stmt = select(ISMappedData).where(ISMappedData.session_id == uuid.UUID(inp.session_id))
        result = await session.execute(stmt)
        mapped_data_rows = result.scalars().all()

    activity.logger.info("  Found %d mapped_data rows, %d required doctypes",
                         len(mapped_data_rows), len(target_structure.get("required_doctypes", [])))

    # ── 2. Download extracted rows from R2 for each mapped_data ──────────────
    s3 = _get_s3_client()
    mapped_data: Dict[str, Any] = {}
    mapped_data_map: Dict[str, Any] = {}  # doctype → ISMappedData row

    for md_row in mapped_data_rows:
        doctype = md_row.target_doctype
        r2_key = md_row.extracted_rows_r2_path

        if not r2_key:
            activity.logger.warning("  ⚠️ No R2 key for %s, skipping", doctype)
            continue

        try:
            response = s3.get_object(Bucket="clean-data", Key=r2_key)
            rows = json.loads(response["Body"].read().decode("utf-8"))
            mapped_data[doctype] = {
                "rows": rows,
            }
            mapped_data_map[doctype] = md_row
            activity.logger.info("  ✅ Loaded %d rows for %s from R2", len(rows), doctype)
        except Exception as e:
            activity.logger.error("  ❌ Failed to load rows for %s: %s", doctype, e)

    # ── 3. Run validation engine ─────────────────────────────────────────────
    engine = _ValidationEngine()
    report = engine.validate(mapped_data, target_structure)
    v_status = report.get("overall", "pass")
    n_errors = len(report.get("errors", []))
    activity.logger.info("  Validation result: %s | %d errors", v_status, n_errors)

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
    async with AsyncSessionLocal() as session:
        for check in report.get("checks", []):
            doctype = check.get("doctype", "")
            md_row = mapped_data_map.get(doctype)

            # Create ISValidationResult
            result_id = uuid.uuid4()
            session.add(ISValidationResult(
                id=result_id,
                session_id=uuid.UUID(inp.session_id),
                mapped_data_id=md_row.id if md_row else None,
                doctype=doctype,
                overall_status=check["status"],
                report_r2_path=report_key,
                total_errors=len(check.get("errors", [])),
                total_warnings=len(check.get("warnings", [])),
                row_count=check.get("row_count", 0),
            ))

            # Create ISValidationError rows for each error
            for err_msg in check.get("errors", []):
                session.add(ISValidationError(
                    id=uuid.uuid4(),
                    validation_result_id=result_id,
                    doctype=doctype,
                    error_type="missing_required" if "Missing required" in err_msg else "business_rule_violation",
                    error_message=err_msg,
                    severity="error",
                ))

            # Create ISValidationError rows for each warning
            for warn_msg in check.get("warnings", []):
                session.add(ISValidationError(
                    id=uuid.uuid4(),
                    validation_result_id=result_id,
                    doctype=doctype,
                    error_type="invalid_format" if "date format" in warn_msg.lower() else "invalid_type",
                    error_message=warn_msg,
                    severity="warning",
                ))

            # Update ISMappedData.validation_status
            if md_row:
                await session.execute(
                    update(ISMappedData)
                    .where(ISMappedData.id == md_row.id)
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

    # ── 6. Audit trail ───────────────────────────────────────────────────────
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="validation_run",
        actor="system",
        entity_type="validation",
        details={"overall": v_status, "errors": n_errors, "doctypes_checked": len(report.get("checks", []))},
        result="success",
    )

    activity.logger.info("✅ validate_mapped_data done | overall=%s errors=%d", v_status, n_errors)
    return v_status