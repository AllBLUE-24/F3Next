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
_GRAPH_PATH = _KB_DIR / "erpnext_doctype_graph.json"

from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings
from containers.implementation.mapping_agent.corpus_merge import dedupe_key_for
from shared.kb.policy_loaders import get_is_import_rules, get_link_resolution_policy


def _load_graph() -> Dict:
    """Load doctype graph; returns empty dict on any failure."""
    try:
        with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_field_mappings() -> Dict:
    """Load composed field mappings from modular KB."""
    return compose_field_mappings()

import boto3
from botocore.config import Config
from temporalio import activity

from shared.models.is_status import NodeStatusEnvelope


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
        self._kb_rules = get_is_import_rules()
        self._kb_messages = self._kb_rules.get("messages") or {}
        self._link_policy = get_link_resolution_policy()

    def _format_kb_message(self, key: str, **ctx: Any) -> str:
        template = self._kb_messages.get(key) or ""
        if not template:
            return ""
        out = template
        for k, v in ctx.items():
            out = out.replace("{" + k + "}", str(v))
        return out

    def _get_required_fields(self, doctype: str) -> List[str]:
        """Read required_fields from graph, then KB is_import_rules, then hardcoded fallback."""
        graph_fields = (
            self._graph.get("doctypes", {})
                       .get(doctype, {})
                       .get("required_fields", [])
        )
        kb_fields = (self._kb_rules.get("required_fields_by_doctype") or {}).get(doctype, [])
        fields = graph_fields if graph_fields else (kb_fields if kb_fields else self._REQUIRED_FIELDS_FALLBACK.get(doctype, []))
        return self._normalise_required_fields(fields or [])

    @staticmethod
    def _normalise_required_fields(fields: List[str]) -> List[str]:
        """
        Graph required_fields may include descriptive strings like:
          'items (item_code, qty, rate)' or 'paid_to/paid_from'
        Normalize them into real fieldnames so validation reports actionable errors.
        """
        out: List[str] = []
        seen: set = set()

        for raw in fields or []:
            s = str(raw or "").strip()
            if not s:
                continue
            # "items (a, b)" -> "items"
            if "(" in s:
                s = s.split("(", 1)[0].strip()
            # "paid_to/paid_from" -> ["paid_to", "paid_from"]
            parts = [p.strip() for p in s.split("/") if p.strip()]
            for p in parts or [s]:
                # Also handle "field - note" style
                p2 = p.split(" ", 1)[0].strip()
                if p2 and p2 not in seen:
                    seen.add(p2)
                    out.append(p2)

        return out

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
                opts_raw = cfg["options"]
                if isinstance(opts_raw, list):
                    opts = [str(o).strip() for o in opts_raw if str(o).strip()]
                elif isinstance(opts_raw, str):
                    parsed_opts = None
                    try:
                        maybe_json = json.loads(opts_raw)
                        if isinstance(maybe_json, list):
                            parsed_opts = maybe_json
                    except Exception:
                        parsed_opts = None
                    if parsed_opts is not None:
                        opts = [str(o).strip() for o in parsed_opts if str(o).strip()]
                    else:
                        opts = [o.strip() for o in opts_raw.split("\n") if o.strip()]
                else:
                    opts = [str(opts_raw).strip()] if str(opts_raw).strip() else []
                if opts:
                    enum_rules[cfg.get("fieldname", _fn)] = opts
        if enum_rules:
            return enum_rules
        kb_enums = (self._kb_rules.get("enum_fields_by_doctype") or {}).get(doctype, {})
        if kb_enums:
            return kb_enums
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
            elif check["status"] == "partial" and report["overall"] == "pass":
                report["overall"] = "partial"
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

        if report["overall"] == "pass" and report["warnings"]:
            report["overall"] = "partial"

        return report

    def merge_ler_unresolvable(
        self,
        report: Dict[str, Any],
        ler_report: Dict[str, Any],
        *,
        mapped_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append KB link-missing messages for LER misses (post-rewrite)."""
        from containers.implementation.is_common.gap_report import gap_from_ler_info
        from containers.implementation.is_common.ler_greenfield import (
            classify_ler_unresolvable,
            resolve_link_target_doctype,
        )

        unres = ler_report.get("unresolvable_values") or []
        if not unres:
            return report

        rule_id = (
            (self._kb_rules.get("link_rules") or [{}])[0].get("rule_id")
            or self._link_policy.get("is_link_missing_rule_id")
            or "is_link_missing_post_ler"
        )

        by_doctype: Dict[str, Dict[str, Any]] = {
            c["doctype"]: c for c in report.get("checks", []) if c.get("doctype")
        }
        mapped = mapped_data or {}
        ler_gaps: List[Dict[str, Any]] = list(report.get("ler_gaps") or [])

        for entry in unres:
            if not isinstance(entry, dict):
                continue
            dt = entry.get("doctype") or "Unknown"
            field = entry.get("field") or entry.get("fieldname") or "link"
            value = entry.get("value") or entry.get("raw_value") or ""
            target = resolve_link_target_doctype(entry)
            disposition, msg = classify_ler_unresolvable(entry, mapped)

            check = by_doctype.get(dt)
            if not check:
                check = {"doctype": dt, "status": "pass", "errors": [], "warnings": [], "row_count": 0}
                report.setdefault("checks", []).append(check)
                by_doctype[dt] = check

            if disposition == "info":
                check["warnings"].append(msg)
                if check["status"] == "pass":
                    check["status"] = "partial"
                report.setdefault("warnings", []).append(msg)
                ler_gaps.append(
                    gap_from_ler_info(
                        link_target=str(target),
                        value=str(value),
                        doctype=str(dt),
                        field=str(field),
                    ).to_dict()
                )
                if report.get("overall") == "pass":
                    report["overall"] = "partial"
                continue

            check["errors"].append(msg)
            check["status"] = "fail"
            report.setdefault("errors", []).append(msg)
            report["overall"] = "fail"
            ler_gaps.append({
                "field": field,
                "doctype": dt,
                "question": msg,
                "severity": "blocking",
                "rule_id": rule_id,
                "metadata": {
                    "origin": "ler",
                    "tier": "critical",
                    "resolution": "ask_user",
                    "link_target": target,
                    "target_doctype": target,
                    "value": value,
                },
            })

        if ler_gaps:
            report["ler_gaps"] = ler_gaps

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

        # Required-field check: scan first 10 rows (items must be non-empty child rows).
        required = self._get_required_fields(doctype)
        if rows and required:
            from containers.implementation.is_common.field_presence import (
                field_present_in_mapped_row,
            )

            sample_rows = [r for r in rows[:10] if isinstance(r, dict)]
            for field in required:
                if not any(field_present_in_mapped_row(field, row) for row in sample_rows):
                    msg = self._format_kb_message("missing_required_field", field=field)
                    check["errors"].append(msg or f"Missing required field: {field}")
                    check["status"] = "fail"

        # Row-level required VALUES — identity + mandatory fields must be non-empty.
        identity_field = dedupe_key_for(doctype)
        value_check_fields: List[str] = list(required)
        if identity_field and identity_field not in value_check_fields:
            value_check_fields.insert(0, identity_field)

        if rows and value_check_fields:
            from containers.implementation.is_common.field_presence import (
                field_present_in_mapped_row,
            )

            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                for field in value_check_fields:
                    if not field_present_in_mapped_row(field, row):
                        msg = self._format_kb_message(
                            "empty_row_value", row=i + 1, field=field,
                        )
                        check["errors"].append(
                            msg or f"Row {i + 1}: empty required value for '{field}'"
                        )
                        check["status"] = "fail"

        # Cross-entity leak detection (Supplier row with customer_name only, etc.)
        if rows and doctype in ("Supplier", "Customer"):
            leak_field = "customer_name" if doctype == "Supplier" else "supplier_name"
            identity = identity_field or ("supplier_name" if doctype == "Supplier" else "customer_name")
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                cross_val = row.get(leak_field)
                id_val = row.get(identity)
                if cross_val and str(cross_val).strip() and (
                    id_val is None or not str(id_val).strip()
                ):
                    msg = self._format_kb_message("entity_leak", row=i + 1, doctype=doctype)
                    check["errors"].append(
                        msg or (
                            f"Row {i + 1}: {doctype} record has '{leak_field}' but empty '{identity}'"
                        )
                    )
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

        if check["status"] == "pass" and check["warnings"]:
            check["status"] = "partial"

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
    retry_feedback: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="validate_mapped_data")
async def validate_mapped_data(inp: ValidateInput) -> Any:
    activity.logger.info("▶ validate_mapped_data started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import (
        ISCompanyProfile,
        ISSession, ISTargetStructure, ISMappedData,
        ISValidationResult, ISValidationError,
    )
    from sqlalchemy import select, update

    # ── 1. Read target_structure from is_target_structures ───────────────────
    defaults_context: Dict[str, Any] = {}
    async with AsyncSessionLocal() as session:
        prof_stmt = (
            select(ISCompanyProfile.company_name)
            .where(ISCompanyProfile.session_id == uuid.UUID(inp.session_id))
            .order_by(ISCompanyProfile.version.desc())
            .limit(1)
        )
        prof_res = await session.execute(prof_stmt)
        company_name = prof_res.scalar_one_or_none()
        if company_name:
            defaults_context = {"company_name": str(company_name)}
        elif inp.company_slug and inp.company_slug not in ("unknown", ""):
            defaults_context = {
                "company_name": inp.company_slug.replace("-", " ").replace("_", " ").title(),
            }

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
        stmt = (
            select(ISMappedData)
            .where(ISMappedData.session_id == uuid.UUID(inp.session_id))
            .limit(100)
        )
        result = await session.execute(stmt)
        mapped_data_rows = result.scalars().all()

    activity.logger.info("  Found %d mapped_data rows to validate", len(mapped_data_rows))

    # ── 2. Download mapped payloads from R2 (merge per doctype) ─────────────
    s3 = _get_s3_client()
    mapped_data: Dict[str, Any] = {}
    mapped_data_map: Dict[str, Any] = {}  # doctype → ISMappedData row (representative)
    source_files_by_doctype: Dict[str, List[str]] = {}

    from containers.implementation.mapping_agent.corpus_merge import (
        aggregate_mapped_data_rows,
        load_r2_json,
    )

    aggregated = aggregate_mapped_data_rows(mapped_data_rows)

    for md_row in mapped_data_rows:
        doctype = md_row.target_doctype
        source_files_by_doctype.setdefault(doctype, [])
        if md_row.source_filename and md_row.source_filename not in source_files_by_doctype[doctype]:
            source_files_by_doctype[doctype].append(md_row.source_filename)

    for doctype, agg in aggregated.items():
        r2_key = agg.get("r2_path")
        if not r2_key:
            activity.logger.warning("  ⚠️ No mapped payload R2 key for %s, skipping", doctype)
            continue

        try:
            payload_json = load_r2_json(s3, "clean-data", r2_key)
            if not isinstance(payload_json, dict):
                activity.logger.warning("  ⚠️ Invalid payload for %s, skipping", doctype)
                continue

            records = payload_json.get("records", [])
            normalized_payload = payload_json
            try:
                from containers.implementation.mapping_agent.defaults import normalize_mapped_payload

                normalized_payload = normalize_mapped_payload(
                    doctype, payload_json, context=defaults_context or None
                )
                if normalized_payload.get("records") != payload_json.get("records"):
                    s3.put_object(
                        Bucket="clean-data",
                        Key=r2_key,
                        Body=json.dumps(normalized_payload, indent=2, default=str).encode("utf-8"),
                        ContentType="application/json",
                    )
                    activity.logger.info(
                        "  🔧 Applied KB defaults to %s payload (%d records) → R2 updated",
                        doctype,
                        len(normalized_payload.get("records") or []),
                    )
            except Exception as e:
                activity.logger.warning("  ⚠️ KB defaults injection failed for %s: %s", doctype, e)

            mapped_data[doctype] = normalized_payload
            mapped_data_map[doctype] = next(
                (r for r in mapped_data_rows if r.target_doctype == doctype),
                None,
            )
            activity.logger.info(
                "  ✅ Loaded merged payload for %s from R2 (%d records, sources=%s)",
                doctype,
                len(normalized_payload.get("records") or []),
                source_files_by_doctype.get(doctype, []),
            )
        except Exception as e:
            activity.logger.error("  ❌ Failed to load payload for %s: %s", doctype, e)

    slug = inp.company_slug or "unknown"

    # ── 2.4 Transactional party stubs (SO/PO refs → Customer/Supplier masters) ──
    try:
        from containers.implementation.is_common.transactional_party_stubs import (
            derive_transactional_party_masters,
        )

        mapped_data, stub_audit = derive_transactional_party_masters(mapped_data)
        for entry in stub_audit:
            master_dt = entry.get("master_doctype")
            if not master_dt:
                continue
            r2_key = (aggregated.get(master_dt) or {}).get("r2_path")
            if not r2_key:
                r2_key = f"{slug}/{inp.project_id}/mappings/mapped_payloads/{master_dt}.json"
            payload = mapped_data.get(master_dt)
            if isinstance(payload, dict):
                s3.put_object(
                    Bucket="clean-data",
                    Key=r2_key,
                    Body=json.dumps(payload, indent=2, default=str).encode("utf-8"),
                    ContentType="application/json",
                )
                activity.logger.info(
                    "  ➕ Transactional party stubs: %s +%d (%s)",
                    master_dt,
                    entry.get("stubs_added"),
                    ", ".join(entry.get("names") or []),
                )
    except Exception as e:
        activity.logger.warning("  ⚠️ Transactional party stub enrichment failed: %s", e)

    # ── 2.5 LER — resolve link fields against live ERP (same path as import Pass 2.5)
    r2_keys_by_doctype = {
        dt: (aggregated.get(dt) or {}).get("r2_path", "")
        for dt in mapped_data
        if (aggregated.get(dt) or {}).get("r2_path")
    }
    ler_report: Dict[str, Any] = {"skipped": True}
    try:
        from containers.implementation.ler_apply import apply_ler_to_session_mapped_data

        ler_report = await apply_ler_to_session_mapped_data(
            project_id=inp.project_id,
            company_slug=inp.company_slug or "unknown",
            mapped_data=mapped_data,
            s3=s3,
            r2_keys_by_doctype=r2_keys_by_doctype,
            log=activity.logger,
        )
        if not ler_report.get("skipped"):
            n_unres = len(ler_report.get("unresolvable_values") or [])
            activity.logger.info(
                "  LER validate: corrections=%d unresolvable=%d",
                len(ler_report.get("corrections") or []),
                n_unres,
            )
    except Exception as e:
        activity.logger.warning("  LER validate skipped: %s", e)

    # ── 3. Run validation engine ─────────────────────────────────────────────
    start_time = datetime.now()
    # Load context files so engine can read required_fields + enum rules from JSON
    engine = _ValidationEngine(graph=_load_graph(), field_mappings=_load_field_mappings())
    report = engine.validate(mapped_data, target_structure)
    if not ler_report.get("skipped"):
        report = engine.merge_ler_unresolvable(report, ler_report, mapped_data=mapped_data)

    from shared.models.validation_report import enrich_checks_with_sources

    report = enrich_checks_with_sources(report, source_files_by_doctype)
    if inp.retry_feedback:
        activity.logger.info(
            "  Quality gate retry feedback (validate): %s",
            inp.retry_feedback[:200],
        )

    duration = (datetime.now() - start_time).total_seconds()
    
    v_status = report.get("overall", "pass")
    n_errors = len(report.get("errors", []))
    n_warnings = len(report.get("warnings", []))
    activity.logger.info("  Validation result: %s | %d errors, %d warnings", v_status, n_errors, n_warnings)

    # ── 4. Upload validation report to R2 ────────────────────────────────────
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
                    total_records_checked=check.get("row_count", 0),
                    row_count=check.get("row_count", 0),
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
                if check["status"] == "pass":
                    mapped_status = "passed"
                elif check["status"] == "partial":
                    mapped_status = "partial"
                else:
                    mapped_status = "failed"
                await session.execute(
                    update(ISMappedData)
                    .where(ISMappedData.id == mapped_data_id)
                    .values(validation_status=mapped_status)
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
    # Build structured envelope (node remains deterministic; this is only a contract change)
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    for msg in report.get("errors", []) or []:
        errors.append({"code": "VALIDATION_ERROR", "message": str(msg)})
    for msg in report.get("warnings", []) or []:
        warnings.append({"code": "VALIDATION_WARNING", "message": str(msg)})

    from containers.implementation.mapping_agent.corpus_merge import (
        filename_conflicts_with_doctype,
        filename_implied_doctype,
    )

    source_file_conflicts: List[Dict[str, Any]] = []
    for check in report.get("checks", []) or []:
        if not isinstance(check, dict):
            continue
        dt = check.get("doctype") or ""
        for src in check.get("source_files") or []:
            if filename_conflicts_with_doctype(str(src), dt):
                source_file_conflicts.append(
                    {
                        "file": src,
                        "assigned_doctype": dt,
                        "implied_doctype": filename_implied_doctype(str(src)),
                    }
                )

    primary = {
        "overall": v_status,
        "error_count": n_errors,
        "warning_count": n_warnings,
        "report_r2_path": report_key,
        "doctypes_checked": len(report.get("checks", []) or []),
        "checks": report.get("checks", []) or [],
        "source_file_conflicts": source_file_conflicts,
        "ler_gaps": report.get("ler_gaps") or [],
    }

    if v_status == "fail" or errors:
        return NodeStatusEnvelope.failed(primary_result=primary, errors=errors, warnings=warnings)
    if v_status == "partial" or warnings:
        return NodeStatusEnvelope.partial(primary_result=primary, warnings=warnings)
    return NodeStatusEnvelope.success(primary_result=primary)