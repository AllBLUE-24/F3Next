"""
Import Agent — Temporal activities for the 3-phase ERPNext import.

Prerequisite planning is done in target_agent (Step 8). Each setup_step
arrives here with an `action` field set by the planner:
  - must_create          → user has a data file  → action: create
  - use_default          → baseline values exist  → action: seed_from_baseline
  - auto_created_by_erpnext → ERPNext handles it → action: skip
  - must_create (no file)→ data gap              → action: data_gap

The Pre-flight Seeder runs before row-level import to POST all
`seed_from_baseline` doctypes so link-validation never fails.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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


# ── Knowledge base path ───────────────────────────────────────────────────────

_KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "erpnext"
_BASELINE_PATH = _KB_DIR / "erpnext_deafaults_baseline.json"

# ERPNext site/company setup — no user CSV required; must not block live import.
_ERPNEXT_AUTO_CONFIG = frozenset({
    "Company",
    "Chart of Accounts",
    "Account",
    "Cost Center",
    "Fiscal Year",
    "Currency",
    "Warehouse",
    "Tax Template",
})


def _load_baseline_data() -> Dict[str, List]:
    if not _BASELINE_PATH.exists():
        return {}
    with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Baseline seeder helpers ───────────────────────────────────────────────────

# Maps each doctype to the field name Frappe uses as the primary identifier.
# Used when building the POST body for a baseline seed record.
_DT_NAME_FIELD: Dict[str, str] = {
    "UOM":                      "uom_name",
    "Item Group":               "item_group_name",
    "Customer Group":           "customer_group_name",
    "Supplier Group":           "supplier_group_name",
    "Territory":                "territory_name",
    "Price List":               "price_list_name",
    "Currency":                 "currency_name",
    "Country":                  "country_name",
    "Department":               "department_name",
    "Designation":              "designation_name",
    "Sales Stage":              "stage_name",
    "Lead Source":              "source_name",
    "Incoterm":                 "incoterm",
    "Industry Type":            "industry",
    "Item Attribute":           "attribute_name",
    "Fiscal Year":              "year",
    "Sales Person":             "sales_person_name",
    "Payment Terms Template":   "template_name",
    "Mode of Payment":          "mode_of_payment",
    "Warehouse Type":           "warehouse_type_name",
    "Stock Entry Type":         "purpose",
}

# Doctypes that require company when missing from mapped rows.
_COMPANY_REQUIRED_DOCTYPES = frozenset({
    "BOM",
    "Work Order",
    "Project",
    "Purchase Receipt",
    "Stock Entry",
    "Sales Order",
    "Purchase Order",
    "Delivery Note",
})


def _build_baseline_record(doctype: str, value: str) -> Dict[str, Any]:
    """
    Build the minimal POST body required to create a baseline seed record
    in ERPNext via the Frappe REST API.

    For most simple master doctypes (UOM, Item Group, Territory, etc.) only
    the name field is required. Special cases are handled explicitly.
    """
    # ── Special-case: Payment Terms Template needs at least one child term row
    if doctype == "Payment Terms Template":
        # Parse "Net 15" → credit_days=15; "Net 30" → credit_days=30; fallback=30
        import re as _re
        _days_match = _re.search(r"(\d+)", value)
        _days = int(_days_match.group(1)) if _days_match else 30
        return {
            "template_name": value,
            "terms": [{
                "payment_type": "Percentage",
                "invoice_portion": 100.0,
                "credit_days_based_on": "Day(s) after invoice date",
                "credit_days": _days,
                "description": value,
            }],
        }

    # ── Special-case: Fiscal Year needs start and end dates
    if doctype == "Fiscal Year":
        if value == "2026-2027":
            return {
                "year": value,
                "year_start_date": "2026-04-01",
                "year_end_date": "2027-03-31",
            }
        return {
            "year": value,
            "year_start_date": f"{value}-01-01",
            "year_end_date": f"{value}-12-31",
        }

    name_field = _DT_NAME_FIELD.get(doctype)
    if name_field:
        return {name_field: value}

    # Generic fallback: try snake_case of doctype + "_name"
    snake = doctype.lower().replace(" ", "_")
    return {f"{snake}_name": value}


from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings

# ── Dynamic link field discovery ─────────────────────────────────────────────


def _build_link_field_index() -> Dict[str, str]:
    """
    Reads composed field mappings at module load time and extracts every field
    where fieldtype == "Link", returning { fieldname: target_doctype }.

    This is the authoritative source — fixing a wrong fieldtype in the JSON
    file is all that's needed to fix a LinkValidationError, no Python changes
    required.  Falls back to an empty dict if the file cannot be read.
    """
    index: Dict[str, str] = {}
    try:
        _data = compose_field_mappings()
        for _dt_cfg in _data.get("doctypes", {}).values():
            for _field_cfg in _dt_cfg.get("field_mappings", {}).values():
                if _field_cfg.get("fieldtype") == "Link":
                    target = _field_cfg.get("options")
                    fieldname = _field_cfg.get("fieldname")
                    if target and isinstance(target, str) and fieldname:
                        index[fieldname] = target
                        # Also index any synonyms declared in the schema
                        for syn in _field_cfg.get("user_input_synonyms", []):
                            if syn and syn not in index:
                                index[syn] = target
    except Exception:
        pass  # non-fatal; fall back to manual additions below
    return index


# Built once at module import (~5 ms). Contains every Link field from
# field_mappings.json. Adding/fixing entries there auto-updates this index.
_SCHEMA_LINK_INDEX: Dict[str, str] = _build_link_field_index()

# Final merged dict: schema-derived index + manual extras for field aliases
# and fields that live outside the schema file's covered doctypes.
# Schema index takes priority so the JSON file stays authoritative.
_KNOWN_LINK_FIELDS: Dict[str, str] = {
    # ── Manual extras not in field_mappings.json ─────────────────────────────
    # Payment aliases
    "payment_terms_template":         "Payment Terms Template",
    "default_payment_terms":          "Payment Terms Template",
    "payment_mode":                   "Mode of Payment",
    # Price list aliases
    "selling_price_list":             "Price List",
    "buying_price_list":              "Price List",
    # Warehouse aliases
    "default_warehouse":              "Warehouse",
    "source_warehouse":               "Warehouse",
    "target_warehouse":               "Warehouse",
    # UOM aliases
    "purchase_uom":                   "UOM",
    "sales_uom":                      "UOM",
    # CRM / classification
    "lead_source":                    "Lead Source",
    "market_segment":                 "Market Segment",
    "sales_person":                   "Sales Person",
    # ── Schema-derived index (overrides manual if conflict) ───────────────────
    **_SCHEMA_LINK_INDEX,
}

# Doctypes that require complex structured data (child tables, multi-field bodies).
# The dynamic seeder will NOT attempt to auto-create these.
#
# PROTOCOL: Prefer setting seeding_complexity="complex" in erpnext_doctype_graph.json.
# This set is the FALLBACK for doctypes not yet defined in the graph.
# Do NOT add new entries here — add them to the graph JSON instead.
_DYNAMIC_SEED_BLACKLIST: set = {
    "Account",
    "Tax Template",
    "Warehouse",
    "Fiscal Year",
    "Company",
    "BOM",
    "Payment Entry",
    "Sales Invoice",
    "Purchase Invoice",
    "Cost Center",
    # Requires child payment_terms rows — seeded by Pass 1 via baseline with
    # structured records built by _build_baseline_record special case:
    "Payment Terms Template",
}

_GRAPH_PATH_FOR_SEED = _KB_DIR / "erpnext_doctype_graph.json"


def _is_seed_blacklisted(doctype: str) -> bool:
    """Check if doctype should be skipped by the dynamic seeder.

    Reads seeding_complexity from erpnext_doctype_graph.json first.
    Falls back to the static _DYNAMIC_SEED_BLACKLIST set if not found in graph.
    This means existing blacklisted doctypes still work even before graph is updated.
    """
    try:
        with open(_GRAPH_PATH_FOR_SEED, "r", encoding="utf-8") as _f:
            _graph = json.load(_f)
        complexity = (
            _graph.get("doctypes", {})
                  .get(doctype, {})
                  .get("seeding_complexity")
        )
        if complexity is not None:
            return complexity in ("complex", "skip")
    except Exception:
        pass  # fall through to static blacklist
    return doctype in _DYNAMIC_SEED_BLACKLIST


async def _discover_name_field(
    doctype: str,
    adapter,
    cache: dict,
) -> str:
    """
    Fetch the Frappe DocType schema to find the primary name/title field.
    Checks _DT_NAME_FIELD first (static lookup), then falls back to a live
    Frappe API call that inspects the doctype's field list.
    Result is stored in `cache` to avoid repeated API calls within a single run.
    
    NOW USES ERPAdapter instead of direct httpx client.
    """
    if doctype in cache:
        return cache[doctype]

    # Static lookup first — fastest path
    if doctype in _DT_NAME_FIELD:
        cache[doctype] = _DT_NAME_FIELD[doctype]
        return _DT_NAME_FIELD[doctype]

    # Live API fallback: inspect the DocType schema
    try:
        doc = await adapter.get_record("DocType", doctype, fields=["fields"])
        schema_fields = doc.get("fields", [])
        for f in schema_fields:
            if f.get("fieldtype") == "Data" and f.get("reqd") == 1:
                cache[doctype] = f["fieldname"]
                return f["fieldname"]
    except Exception:
        pass  # fall through to generic fallback

    # Generic fallback: snake_case_name
    fallback = doctype.lower().replace(" ", "_") + "_name"
    cache[doctype] = fallback
    return fallback


async def _dynamic_seed_doctype(
    doctype: str,
    referenced_values: List[str],
    adapter,
    name_field_cache: dict,
    logger,
) -> Dict[str, int]:
    """
    Dynamically seeds a doctype that is NOT in the static baseline.

    1. Fetches all existing records from ERPNext (names only).
    2. Diffs against `referenced_values`.
    3. Creates only the missing records using the discovered name field.

    NOW USES ERPAdapter instead of direct httpx client.

    Returns {"seeded": N, "already": N, "failed": N}.
    """
    seeded = 0
    already = 0
    failed = 0

    # Step 1 — fetch existing names from ERPNext
    existing: set = set()
    try:
        rows = await adapter.list_records(doctype, fields=["name"], limit=500)
        for row in rows:
            if row.get("name"):
                existing.add(row["name"])
    except Exception as e:
        logger.warning("  ⚠️  Could not fetch existing %s records: %s", doctype, e)

    # Step 2 — determine what's missing
    to_create = [v for v in referenced_values if v and v not in existing]
    for val in referenced_values:
        if val and val in existing:
            already += 1

    if not to_create:
        return {"seeded": seeded, "already": already, "failed": failed}

    # Step 3 — discover the name field (cached)
    name_field = await _discover_name_field(doctype, adapter, name_field_cache)

    # Step 4 — create each missing value
    for val in to_create:
        if doctype == "Stock Entry Type":
            record = {"purpose": val, "name": val}
        else:
            record = {name_field: val}
        try:
            await adapter.create_record(doctype, record)
            seeded += 1
        except ValueError as exc:
            # Adapter raises ValueError for 4xx errors (including 409/417 duplicates)
            err_text = str(exc)
            if "already exist" in err_text.lower() or "duplicate" in err_text.lower():
                already += 1
            else:
                failed += 1
                logger.warning("  ⚠️  Dynamic seed %s '%s' failed: %s", doctype, val, err_text)
        except Exception as exc:
            failed += 1
            logger.warning("  ⚠️  Dynamic seed %s '%s' failed: %s", doctype, val, exc)

    return {"seeded": seeded, "already": already, "failed": failed}


async def _run_baseline_preflight_seed(
    adapter,
    phases: Dict[str, Any],
    logger,
    *,
    dry_run: bool,
    base_url: Optional[str],
) -> tuple[set, Dict[str, set]]:
    """
    Legacy Pass-1 baseline catalog seed — skipped when ERP setup is already done.

    Post-onboarding / live sites: Company exists → ERPNext fixtures are present;
    missing masters surface as per-row import errors (Pass 2 / create_record).

    Greenfield: setup wizard in ensure_site_prerequisites provisions fixtures;
    no per-currency/UOM catalog loop.

    Returns (seen_doctypes, seen_values_by_doctype) for Pass 2 idempotency.
    """
    seen_seed_doctypes: set = set()
    seen_seed_values: Dict[str, set] = {}

    if dry_run:
        logger.info("  🌱  PRE-FLIGHT SEEDER — dry_run mode, skipping baseline catalog")
        return seen_seed_doctypes, seen_seed_values

    if not base_url:
        return seen_seed_doctypes, seen_seed_values

    from containers.implementation.import_agent.site_prerequisites import (
        discover_live_company,
        site_has_company,
    )

    if await site_has_company(adapter, logger):
        live = await discover_live_company(adapter, None, logger)
        name = (live or {}).get("name", "?")
        logger.info(
            "  🌱  PRE-FLIGHT SEEDER — skipped (Company '%s' on site; trust ERPNext setup)",
            name,
        )
        return seen_seed_doctypes, seen_seed_values

    logger.info(
        "  🌱  PRE-FLIGHT SEEDER — skipped (greenfield; setup wizard provisions fixtures next)",
    )
    return seen_seed_doctypes, seen_seed_values


async def _bulk_pre_resolve_phase_rows(
    steps: List[Dict],
    s3,
    adapter,
    known_link_fields: Dict[str, str],
    logger,
    company_abbr: str = "",
) -> tuple[Dict[str, List[Dict]], Dict[str, Dict[str, Any]]]:
    """
    Pass 2.5: bulk pre-resolve link fields for all create-action steps in a phase.

    Returns:
        pre_resolved_cache: {r2_key: [rewritten rows]}
        step_summaries: {r2_key: resolution_summary}
    """
    from shared.entity_resolution.rows import (
        apply_resolution_map_to_rows,
        collect_link_targets_from_rows,
    )
    from shared.entity_resolution.ler import build_resolution_map

    pre_resolved_cache: Dict[str, List[Dict]] = {}
    step_summaries: Dict[str, Dict[str, Any]] = {}
    all_link_targets: Dict[str, set] = {}
    step_payloads: List[tuple] = []

    for step in steps:
        if step.get("action") != "create":
            continue
        r2_key = step.get("data_source")
        if not r2_key or r2_key in ("none", "pending_mapping"):
            continue
        try:
            resp = s3.get_object(Bucket="clean-data", Key=r2_key)
            payload = json.loads(resp["Body"].read().decode("utf-8"))
            rows = payload.get("records", [])
        except Exception as e:
            logger.warning("  Pass 2.5: could not read R2 key %s: %s", r2_key, e)
            continue

        payload_link_fields: Dict[str, str] = payload.get("link_fields", {})
        effective_link_fields: Dict[str, str] = {**known_link_fields, **payload_link_fields}
        targets = collect_link_targets_from_rows(rows, effective_link_fields)
        for target_dt, vals in targets.items():
            all_link_targets.setdefault(target_dt, set()).update(vals)
        step_payloads.append((r2_key, step.get("doctype", ""), rows, effective_link_fields))

    if not all_link_targets:
        logger.info("  Pass 2.5 — No link targets to resolve")
        return pre_resolved_cache, step_summaries

    logger.info(
        "  Pass 2.5 — Bulk resolving %d doctype(s): %s",
        len(all_link_targets),
        ", ".join(sorted(all_link_targets.keys())),
    )

    resolution_map = await build_resolution_map(
        adapter,
        all_link_targets,
        log=logger,
        preferred_abbr=company_abbr or None,
    )

    for r2_key, step_dt, rows, effective_link_fields in step_payloads:
        rewritten, summary = apply_resolution_map_to_rows(
            rows,
            effective_link_fields,
            resolution_map,
        )
        pre_resolved_cache[r2_key] = rewritten
        summary["doctype"] = step_dt
        step_summaries[r2_key] = summary

        for hit in summary.get("unresolvable_values", []):
            logger.warning(
                "  Pass 2.5: unresolvable %s.%s = '%s' (target %s)",
                step_dt,
                hit.get("field"),
                hit.get("value"),
                hit.get("target_doctype"),
            )
        for corr in summary.get("corrections", []):
            logger.info(
                "  Pass 2.5: resolved %s.%s '%s' -> '%s'",
                step_dt,
                corr.get("field"),
                corr.get("original"),
                corr.get("corrected"),
            )

    return pre_resolved_cache, step_summaries


async def _submit_after_create_if_needed(
    adapter,
    doctype: str,
    create_result: dict,
    *,
    auto_submit_override: Optional[bool] = None,
    commit_confidence: float = 1.0,
    phase_child_doctypes: Optional[set] = None,
    execution_confirmed: bool = False,
    logger,
) -> Optional[dict]:
    """Pass 2.6: submit document after create when unified submit gate allows."""
    from shared.erp_policies.submit_gate import should_submit_after_create

    if not isinstance(create_result, dict):
        return None
    doc_name = create_result.get("name")
    if not doc_name:
        return None

    docstatus = create_result.get("docstatus", 0)
    if docstatus == 1:
        return {"doctype": doctype, "name": doc_name, "action": "already_submitted"}

    if not should_submit_after_create(
        doctype,
        context="import",
        commit_confidence=commit_confidence,
        phase_child_doctypes=phase_child_doctypes,
        execution_confirmed=execution_confirmed,
        override=auto_submit_override,
    ):
        logger.info(
            "  Pass 2.6: %s '%s' left as draft (submit gate: confidence=%.2f confirmed=%s)",
            doctype,
            doc_name,
            commit_confidence,
            execution_confirmed,
        )
        return None

    try:
        submitted = await adapter.submit_document(doctype, str(doc_name))
        logger.info("  Pass 2.6: submitted %s '%s'", doctype, doc_name)
        return {
            "doctype": doctype,
            "name": doc_name,
            "action": "submitted",
            "docstatus": submitted.get("docstatus", 1),
        }
    except Exception as exc:
        logger.warning("  Pass 2.6: submit failed for %s '%s': %s", doctype, doc_name, exc)
        return {
            "doctype": doctype,
            "name": doc_name,
            "action": "submit_failed",
            "error": str(exc),
        }


async def _load_commit_confidence(session_id: str) -> float:
    """IS COMMIT confidence from latest data readiness assessment."""
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISDataReadinessAssessment
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISDataReadinessAssessment)
                .where(ISDataReadinessAssessment.session_id == uuid.UUID(session_id))
                .order_by(ISDataReadinessAssessment.created_at.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row and row.import_readiness_score is not None:
                return float(row.import_readiness_score)
    except Exception:
        pass
    return 1.0


async def _resolve_erp_adapter(inp, logger):
    """Build ERPNext adapter from input + Project.deployment_details."""
    from shared.database.db import AsyncSessionLocal
    from shared.models.core import Project
    from shared.erp_adapters.registry import get_adapter
    from sqlalchemy import select

    base_url = (getattr(inp, "erpnext_base_url", None) or "").rstrip("/")
    api_token = getattr(inp, "erpnext_api_key", None) or ""
    verify_ssl = True
    allow_insecure_ssl = True
    project_id = getattr(inp, "project_id", None)

    if project_id:
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Project).where(Project.id == uuid.UUID(project_id))
                res = await db.execute(stmt)
                project = res.scalar_one_or_none()
                if project and project.deployment_details:
                    details = project.deployment_details
                    if not base_url:
                        base_url = (details.get("site_url", "") or "").rstrip("/")
                        logger.info("  🔑 Auto-resolved base_url from Project.deployment_details: %s", base_url)
                    if not api_token:
                        dk = details.get("api_key", "")
                        ds = details.get("api_secret", "")
                        if dk and ds:
                            api_token = f"{dk}:{ds}"
                            logger.info("  🔑 Auto-resolved API credentials from Project.deployment_details")
                    v_ssl = details.get("verify_ssl")
                    if v_ssl is not None:
                        verify_ssl = str(v_ssl).lower() not in ("false", "0", "no")
                    a_ssl = details.get("allow_insecure_ssl")
                    if a_ssl is not None:
                        allow_insecure_ssl = str(a_ssl).lower() not in ("false", "0", "no")
        except Exception as e:
            logger.error("  ❌ Failed to auto-resolve credentials from Project: %s", e)

    adapter_profile = {
        "erp_type": "erpnext",
        "erp_url": base_url,
        "api_key": api_token.split(":")[0] if ":" in api_token else "",
        "api_secret": api_token.split(":")[1] if ":" in api_token else "",
        "verify_ssl": verify_ssl,
        "allow_insecure_ssl": allow_insecure_ssl,
    }
    return base_url, get_adapter(adapter_profile)


# ── Embedded service logic ────────────────────────────────────────────────────

class _ImportEngine:
    def build_plan(
        self,
        setup_steps: List[Dict],
        mapped_data_dict: Dict[str, Dict],
        validation_status: str,
        playbook_context: str = "",
    ) -> Dict[str, Any]:
        from containers.implementation.is_common.doctype_resolver import lookup_normalized, resolve_doctype

        if validation_status == "fail":
            return {
                "status": "blocked",
                "reason": "Validation failed. Fix errors before import.",
            }

        _PHASE_A_AUTO_SETUP = {
            "Company":             "discover_from_site",
            "Chart of Accounts":   "auto_from_company",
            "Account":             "auto_from_company",
            "Cost Center":         "auto_from_company",
            "Fiscal Year":         "discover_from_site",
            "Currency":            "seed_from_baseline",
            "Warehouse":           "seed_from_config",
            "Tax Template":        "skip",
        }

        # ── PROTOCOL-COMPLIANT: Phases are derived from setup_steps data. ────────────
        # Pre-seed the 3 standard phases so existing plans never break.
        # Any additional phases found in setup_steps are added dynamically.
        # This means Phase D (projects) appears automatically once the graph
        # maps its doctypes to 'phase_d_projects'.
        _PHASE_LABEL_MAP = {
            "phase_a_config":        "Configuration Setup",
            "phase_b_master":        "Master Data",
            "phase_c_transactional": "Transactional Data",
        }
        phases: Dict[str, Any] = {
            "phase_a_config":        {"name": "Configuration Setup",  "steps": []},
            "phase_b_master":        {"name": "Master Data",          "steps": []},
            "phase_c_transactional": {"name": "Transactional Data",   "steps": []},
            "phase_d_projects":      {"name": "Project Data",         "steps": []},
        }
        for step_info in setup_steps:
            phase_key = step_info.get("phase", "phase_a_config")
            if phase_key not in phases:
                # Dynamically create any new phase found in setup_steps
                label = _PHASE_LABEL_MAP.get(
                    phase_key,
                    phase_key.replace("phase_", "").replace("_", " ").title() + " Setup"
                )
                phases[phase_key] = {"name": label, "steps": []}
        
        total_steps = 0
        
        for step_idx, step_info in enumerate(setup_steps):
            dt = step_info.get("doctype", "Unknown")
            phase_key = step_info.get("phase", "phase_a_config")
            dt_resolved = resolve_doctype(dt)

            if phase_key not in phases:
                phase_key = "phase_a_config"

            is_mapped = lookup_normalized(mapped_data_dict, dt_resolved) is not None
            # Read the planner's action from Step 8 — do NOT discard it
            planner_action = step_info.get("action", "must_create")

            if dt in _PHASE_A_AUTO_SETUP:
                # Override action — never ask user for files for these
                exec_action = _PHASE_A_AUTO_SETUP[dt]
                data_source = "auto"
                record_count = 0
            elif is_mapped:
                # User has provided a data file — import it row by row
                mapped_entry = lookup_normalized(mapped_data_dict, dt_resolved) or {}
                exec_action  = "create"
                data_source  = mapped_entry.get("r2_path", "pending_mapping")
                record_count = mapped_entry.get("total_rows", 0)
            elif planner_action == "use_default":
                # Values exist in erpnext_deafaults_baseline.json — seed them
                exec_action  = "seed_from_baseline"
                data_source  = "baseline"
                record_count = 0  # will be filled in at seed time
            elif planner_action == "auto_created_by_erpnext":
                # ERPNext creates these automatically on Company setup — skip
                exec_action  = "skip"
                data_source  = "auto"
                record_count = 0
            elif planner_action == "optional_if_absent":
                # Conditional graph node — skip unless user uploaded a file
                exec_action  = "optional_skip"
                data_source  = "none"
                record_count = 0
            else:
                # must_create but no file uploaded — flag as data gap
                exec_action  = "data_gap"
                data_source  = "none"
                record_count = 0

            step_def = {
                "step":        step_idx + 1,
                "doctype":     dt,
                "action":      exec_action,
                "data_source": data_source,
                "records":     record_count,
            }

            phases[phase_key]["steps"].append(step_def)
            total_steps += 1

        return {
            "status": "ready",
            "total_phases": len([p for p in phases.values() if len(p["steps"]) > 0]),
            "total_steps": total_steps,
            "estimated_duration_minutes": max(5, int(total_steps * 0.5)),
            "phases": phases,
        }


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class BuildImportPlanInput:
    session_id: str
    project_id: str
    company_slug: str = "unknown"

@dataclass
class ExecutePhaseInput:
    session_id: str
    phase_id: str
    project_id: str
    company_slug: str = "unknown"
    dry_run: bool = False  # Default to live execution — safety is via double-confirm signals
    erpnext_base_url: Optional[str] = None
    erpnext_api_key: Optional[str] = None
    auto_submit: Optional[bool] = None  # None = follow KB lifecycle policy
    execution_confirmed: bool = False   # True when user approved execution gate
    skip_execution_gate: bool = False   # Harness/dev bypass for execution gate


@dataclass
class PreflightImportInput:
    session_id: str
    phase_id: str
    project_id: str
    company_slug: str = "unknown"
    erpnext_base_url: Optional[str] = None
    erpnext_api_key: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="build_import_plan")
async def build_import_plan(inp: BuildImportPlanInput) -> str:
    """
    Step 12: Generates the 3-Phase execution plan from the already-resolved
    ISTargetStructure (setup_steps are graph-authoritative from Step 8).
    """
    activity.logger.info("▶ build_import_plan started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISTargetStructure, ISDataReadinessAssessment, ISImportPlan
    from sqlalchemy import select

    setup_steps = []
    ready_doctypes = []
    partial_doctypes = []
    
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
            return "error:no_target_structure"

        try:
            setup_steps = json.loads(target_row.setup_steps) if isinstance(target_row.setup_steps, str) else target_row.setup_steps
        except Exception:
            setup_steps = []

        stmt_readiness = (
            select(ISDataReadinessAssessment)
            .where(ISDataReadinessAssessment.session_id == uuid.UUID(inp.session_id))
            .order_by(ISDataReadinessAssessment.created_at.desc())
            .limit(1)
        )
        result_readiness = await session.execute(stmt_readiness)
        readiness_row = result_readiness.scalar_one_or_none()
        if readiness_row:
            ready_doctypes = readiness_row.ready_doctypes or []
            partial_doctypes = readiness_row.partial_doctypes or []
            gap_report = readiness_row.gap_report or {}
            if not partial_doctypes and gap_report.get("partial_doctypes"):
                partial_doctypes = gap_report.get("partial_doctypes", [])
            if not ready_doctypes and gap_report.get("ready_doctypes"):
                ready_doctypes = gap_report.get("ready_doctypes", [])

    # Map target_doctype to ready/partial indicators
    mapped_data_dict = {}
    validation_status = "pass"
    
    def _extract_doctype_names(doctypes_list):
        names = []
        for item in doctypes_list:
            if isinstance(item, dict):
                names.append(item.get("doctype"))
            elif hasattr(item, "doctype"):
                names.append(item.doctype)
            elif isinstance(item, str):
                names.append(item)
        return names

    ready_names = _extract_doctype_names(ready_doctypes)
    partial_names = _extract_doctype_names(partial_doctypes)
    ready_or_partial = set(ready_names) | set(partial_names)

    from containers.implementation.mapping_agent.corpus_merge import filename_implied_doctype
    from containers.implementation.is_common.doctype_resolver import resolve_doctype

    for dt in ready_or_partial:
        if dt:
            canonical = resolve_doctype(dt)
            mapped_data_dict[canonical] = {
                "r2_path": "pending_mapping",
                "total_rows": 0,
            }

    # Corpus expansion: filename-implied doctypes from readiness source files
    for bucket in (ready_doctypes, partial_doctypes):
        for item in bucket or []:
            if not isinstance(item, dict):
                continue
            src = item.get("source_file")
            if src:
                implied = filename_implied_doctype(str(src))
                if implied:
                    mapped_data_dict[resolve_doctype(implied)] = {
                        "r2_path": "pending_mapping",
                        "total_rows": 0,
                    }
            dt_name = item.get("doctype")
            if dt_name:
                mapped_data_dict[resolve_doctype(dt_name)] = {
                    "r2_path": "pending_mapping",
                    "total_rows": 0,
                }

    # ── Fetch professional implementation sequence from pgvector ──────────
    playbook_context = ""
    try:
        from containers.implementation.utils.rag_helper import rag_retrieve
        from shared.models.is_models import ISCompanyProfile
        
        async with AsyncSessionLocal() as session:
            stmt = select(ISCompanyProfile).where(ISCompanyProfile.session_id == uuid.UUID(inp.session_id)).order_by(ISCompanyProfile.version.desc()).limit(1)
            prof = (await session.execute(stmt)).scalar_one_or_none()
            f3iche = prof.f3iche if prof else "universal"

        playbook_chunks = await rag_retrieve(
            f"{f3iche} ERPNext Phase A foundation setup professional sequence",
            "erp_implementation_playbook",
            top_k=4,
        )
        playbook_context = "\n\n".join(playbook_chunks)
        activity.logger.info("  📚 Fetched %d playbook chunks for import plan", len(playbook_chunks))
    except Exception as e:
        activity.logger.warning("  ⚠️ Playbook RAG retrieval failed (non-fatal): %s", e)

    # ── BUILD THE 3-PHASE IMPORT PLAN ─────────────────────────────────────────
    engine = _ImportEngine()
    plan = engine.build_plan(setup_steps, mapped_data_dict, validation_status, playbook_context)
    plan_status = plan.get("status", "blocked")

    slug = inp.company_slug or "unknown"
    plan_key = f"{slug}/{inp.project_id}/_import_plan/plan.json"
    
    final_plan_json = {
        "session_id": inp.session_id,
        "status": plan_status,
        "total_phases": plan.get("total_phases", 0),
        "total_steps": plan.get("total_steps", 0),
        "estimated_duration_minutes": plan.get("estimated_duration_minutes", 0),
        "phases": plan.get("phases", {})
    }

    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket="clean-data",
            Key=plan_key,
            Body=json.dumps(final_plan_json, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:
        activity.logger.error("  ❌ R2 plan upload failed: %s", e)

    plan_id = uuid.uuid4()
    if plan_status == "ready":
        try:
            async with AsyncSessionLocal() as db_session:
                db_session.add(ISImportPlan(
                    id=plan_id,
                    session_id=uuid.UUID(inp.session_id),
                    total_phases=plan.get("total_phases", 0),
                    total_steps=plan.get("total_steps", 0),
                    plan_r2_path=plan_key,
                    phases=plan.get("phases", {}),
                    status="ready",
                ))
                await db_session.commit()
        except Exception as e:
            activity.logger.error("  ❌ Supabase ISImportPlan insert failed: %s", e)

    try:
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="import_plan_created",
            actor="system",
            entity_type="import_plan",
            entity_id=str(plan_id),
            details={"status": plan_status, "phases": plan.get("total_phases"), "steps": plan.get("total_steps")},
            result="success",
        )
    except Exception:
        pass

    return plan_status


@dataclass
class FinalizeImportPlanInput:
    session_id: str
    project_id: str
    company_slug: str = "unknown"


@activity.defn(name="finalize_import_plan")
async def finalize_import_plan(inp: FinalizeImportPlanInput) -> str:
    """
    Step 12b: Post-mapping/validation step. Reads the existing ISImportPlan,
    resolves the pending_mapping actions using the actual ISMappedData records,
    checks if validation failed, and updates the plan in R2 and DB.
    """
    activity.logger.info("▶ finalize_import_plan started | session=%s", inp.session_id)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import (
        ISImportPlan,
        ISMappedData,
        ISValidationResult,
        ISDataReadinessAssessment,
        ISTargetStructure,
    )
    from sqlalchemy import select, update
    from containers.implementation.import_agent.gap_criticality import build_doctype_criticality_map
    from containers.implementation.import_agent.mvp_import_scope import (
        blocks_import_when_unmapped,
        is_out_of_mvp_scope,
        parse_mvp_scope_from_target,
    )
    from containers.implementation.mapping_agent.corpus_merge import load_r2_json

    async with AsyncSessionLocal() as session:
        # 1. Fetch latest import plan
        stmt = (
            select(ISImportPlan)
            .where(ISImportPlan.session_id == uuid.UUID(inp.session_id))
            .order_by(ISImportPlan.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        plan_row = result.scalar_one_or_none()

        if not plan_row:
            activity.logger.warning("  ⚠️ No import plan found to finalize.")
            return "error:no_import_plan"

        # 2. Fetch all mapped data for this session
        stmt_mapped = (
            select(ISMappedData)
            .where(ISMappedData.session_id == uuid.UUID(inp.session_id))
            .limit(100)
        )
        result_mapped = await session.execute(stmt_mapped)
        mapped_rows = result_mapped.scalars().all()

        from containers.implementation.mapping_agent.corpus_merge import (
            aggregate_mapped_data_rows,
            enrich_mapped_dict_from_r2,
            inject_missing_mapped_steps,
        )

        s3 = _get_s3_client()
        mapped_dict = aggregate_mapped_data_rows(mapped_rows)
        mapped_dict = enrich_mapped_dict_from_r2(mapped_dict, s3)

        # 3. Fetch session validation errors
        stmt_val = (
            select(ISValidationResult)
            .where(ISValidationResult.session_id == uuid.UUID(inp.session_id))
            .limit(50)
        )
        result_val = await session.execute(stmt_val)
        val_rows = result_val.scalars().all()
        has_validation_failures = any(v.overall_status == "fail" for v in val_rows)

        stmt_readiness = (
            select(ISDataReadinessAssessment)
            .where(ISDataReadinessAssessment.session_id == uuid.UUID(inp.session_id))
            .order_by(ISDataReadinessAssessment.created_at.desc())
            .limit(1)
        )
        readiness_result = await session.execute(stmt_readiness)
        readiness_row = readiness_result.scalar_one_or_none()
        criticality_map = build_doctype_criticality_map(readiness_row)
        baseline_data = _load_baseline_data()

        target_stmt = (
            select(ISTargetStructure)
            .where(ISTargetStructure.session_id == uuid.UUID(inp.session_id))
            .order_by(ISTargetStructure.created_at.desc())
            .limit(1)
        )
        target_row = (await session.execute(target_stmt)).scalar_one_or_none()
        mvp_seeds: Set[str] = set()
        deferred: Set[str] = set()
        if target_row and target_row.r2_path:
            try:
                target_data = load_r2_json(s3, "clean-data", target_row.r2_path)
                if isinstance(target_data, dict):
                    mvp_seeds, deferred = parse_mvp_scope_from_target(target_data)
            except Exception as exc:
                activity.logger.warning("  ⚠️ Could not load MVP scope from target R2: %s", exc)

        # 4. Update the steps in the plan (+ inject mapped doctypes missing from blueprint)
        slug = inp.company_slug or "unknown"
        phases = plan_row.phases or {}
        phases = inject_missing_mapped_steps(phases, mapped_dict)

        bootstrap_key = f"{slug}/{inp.project_id}/_bootstrap/site_config.json"
        bootstrap_summary: Dict[str, Any] = {}
        try:
            bootstrap_summary = load_r2_json(s3, "clean-data", bootstrap_key)
            if not isinstance(bootstrap_summary, dict):
                bootstrap_summary = {}
        except Exception:
            bootstrap_summary = {}

        from containers.implementation.is_common.site_config_bootstrap import phase_0_steps_from_bootstrap

        derived_config = bootstrap_summary.get("derived_config") or {}
        phase_0_steps = phase_0_steps_from_bootstrap(derived_config)
        for step in phase_0_steps:
            dt = step.get("doctype")
            if dt and dt in mapped_dict:
                step["data_source"] = mapped_dict[dt].get("r2_path", step.get("data_source"))
            elif dt and step.get("data_source") == "site_config_bootstrap":
                step["data_source"] = (
                    f"{slug}/{inp.project_id}/mappings/mapped_payloads/{dt}.json"
                )

        plan_status = "ready"
        has_critical_gap = False
        has_noncritical_gap = False
        if has_validation_failures:
            plan_status = "blocked"

        updated_phases = {}
        optional_gaps: List[str] = []
        for phase_id, phase_data in phases.items():
            steps = phase_data.get("steps", [])
            updated_steps = []
            for step in steps:
                dt = step.get("doctype")
                action = step.get("action")
                unmapped = dt not in mapped_dict
                needs_file = action in (
                    "create",
                    "data_gap",
                    "optional_skip",
                ) or step.get("data_source") == "pending_mapping"

                if needs_file and unmapped:
                    from containers.implementation.is_common.doctype_resolver import resolve_doctype

                    dt_resolved = resolve_doctype(dt or "")
                    baseline_vals = baseline_data.get(dt_resolved) or baseline_data.get(dt or "")

                    if baseline_vals:
                        step["action"] = "seed_from_baseline"
                        step["data_source"] = "baseline"
                        step["records"] = len(baseline_vals)
                        updated_steps.append(step)
                        continue

                    if dt_resolved in _ERPNEXT_AUTO_CONFIG or (dt or "") in _ERPNEXT_AUTO_CONFIG:
                        step["action"] = "skip"
                        step["data_source"] = "auto"
                        step["records"] = 0
                        updated_steps.append(step)
                        continue

                    if action == "optional_skip" or is_out_of_mvp_scope(
                        dt_resolved, mvp_seeds, deferred,
                    ):
                        has_noncritical_gap = True
                        optional_gaps.append(dt or "")
                        step["action"] = "optional_skip"
                        step["data_source"] = "none"
                        step["records"] = 0
                        updated_steps.append(step)
                        continue

                    if not blocks_import_when_unmapped(
                        dt or "", mvp_seeds, deferred, criticality_map, phase_id,
                    ):
                        step["action"] = "optional_skip"
                        step["data_source"] = "none"
                        step["records"] = 0
                        has_noncritical_gap = True
                        optional_gaps.append(dt or "")
                    else:
                        step["action"] = "data_gap"
                        step["data_source"] = "none"
                        step["records"] = 0
                        step["criticality"] = "critical"
                        has_critical_gap = True
                elif needs_file and dt in mapped_dict:
                    step["data_source"] = mapped_dict[dt]["r2_path"]
                    step["records"] = mapped_dict[dt]["total_rows"]
                    if mapped_dict[dt]["validation_status"] == "failed":
                        plan_status = "blocked"
                        has_critical_gap = True
                
                updated_steps.append(step)
            
            updated_phases[phase_id] = {
                "name": phase_data.get("name"),
                "steps": updated_steps
            }

        if phase_0_steps:
            updated_phases = {
                "phase_0_site_config": {
                    "name": "Site Config Bootstrap",
                    "steps": phase_0_steps,
                },
                **updated_phases,
            }

        if has_validation_failures or has_critical_gap:
            plan_status = "blocked"
        elif has_noncritical_gap:
            plan_status = "ready_with_gaps"
        else:
            plan_status = "ready"

        # 5. Upload finalized json plan to R2
        slug = inp.company_slug or "unknown"
        plan_key = f"{slug}/{inp.project_id}/_import_plan/plan.json"
        
        final_plan_json = {
            "session_id": inp.session_id,
            "status": plan_status,
            "total_phases": plan_row.total_phases,
            "total_steps": plan_row.total_steps,
            "estimated_duration_minutes": plan_row.estimated_duration_minutes,
            "phases": updated_phases,
            "optional_gaps": optional_gaps,
        }

        try:
            s3.put_object(
                Bucket="clean-data",
                Key=plan_key,
                Body=json.dumps(final_plan_json, indent=2, default=str).encode("utf-8"),
                ContentType="application/json",
            )
            activity.logger.info("  ✅ Finalized R2 plan uploaded.")
        except Exception as e:
            activity.logger.error("  ❌ R2 finalized plan upload failed: %s", e)

        # 6. Update ISImportPlan database record
        try:
            stmt_update = (
                update(ISImportPlan)
                .where(ISImportPlan.id == plan_row.id)
                .values(
                    phases=updated_phases,
                    status=plan_status,
                )
            )
            await session.execute(stmt_update)
            await session.commit()
            activity.logger.info("  ✅ Finalized ISImportPlan database record updated | id=%s status=%s", plan_row.id, plan_status)
        except Exception as e:
            activity.logger.error("  ❌ Supabase ISImportPlan update failed: %s", e)

    return plan_status


@dataclass
class GetImportPlanPhasesInput:
    session_id: str


@activity.defn(name="get_import_plan_phases")
async def get_import_plan_phases(inp: GetImportPlanPhasesInput) -> List[tuple[str, str]]:
    """
    Reads the import plan from Supabase and returns the ordered list of phases
    to execute: [(phase_id, phase_name), ...]
    """
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportPlan
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISImportPlan)
            .where(ISImportPlan.session_id == uuid.UUID(inp.session_id))
            .order_by(ISImportPlan.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        plan = result.scalar_one_or_none()

    if not plan or not plan.phases:
        # Fallback to standard 3 phases if plan isn't found
        return [
            ("phase_a_config",        "Configuration Setup"),
            ("phase_b_master",        "Master Data"),
            ("phase_c_transactional", "Transactional Data"),
        ]

    from containers.implementation.import_agent.phase_order import sort_phases

    phase_list = [
        (phase_id, phase_data.get("name", phase_id))
        for phase_id, phase_data in sort_phases(plan.phases)
    ]
    return phase_list


@activity.defn(name="preflight_import")
async def preflight_import(inp: PreflightImportInput) -> Dict[str, Any]:
    """
    Read-only preflight for an import phase: link resolution dry-run,
    draft parent scan, financial warnings, execution gate preview.
    """
    activity.logger.info(
        "▶ preflight_import started | session=%s phase=%s",
        inp.session_id,
        inp.phase_id,
    )

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportPlan
    from sqlalchemy import select
    from containers.implementation.import_agent.preflight import run_import_preflight

    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISImportPlan)
            .where(ISImportPlan.session_id == uuid.UUID(inp.session_id))
            .order_by(ISImportPlan.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        import_plan = result.scalar_one_or_none()

    if not import_plan:
        return {"status": "error", "error": "Import plan not found."}

    phases = import_plan.phases or {}
    phase_def = phases.get(inp.phase_id)
    if not phase_def:
        return {"status": "error", "error": f"Phase {inp.phase_id} not in plan."}

    steps = phase_def.get("steps", [])
    base_url, adapter = await _resolve_erp_adapter(inp, activity.logger)
    s3 = _get_s3_client()

    if not base_url:
        return {
            "status": "error",
            "error": "ERPNext base URL not configured.",
            "phase_id": inp.phase_id,
        }

    report = await run_import_preflight(
        phase_id=inp.phase_id,
        steps=steps,
        s3=s3,
        adapter=adapter,
        known_link_fields=_KNOWN_LINK_FIELDS,
        log=activity.logger,
    )
    activity.logger.info(
        "✅ preflight_import done | phase=%s requires_gate=%s",
        inp.phase_id,
        report.get("requires_execution_gate"),
    )
    return report


@activity.defn(name="execute_import_phase")
async def execute_import_phase(inp: ExecutePhaseInput) -> Dict[str, Any]:
    """
    Step 13: Execute (or dry-run) a single import phase by pushing data to ERPNext row by row.
    """
    activity.logger.info("▶ execute_import_phase started | session=%s phase=%s dry_run=%s",
                         inp.session_id, inp.phase_id, inp.dry_run)

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportPlan, ISImportLog
    from sqlalchemy import select, update

    # ── 1. Read import plan from Supabase ────────────────────────────────────
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ISImportPlan)
            .where(ISImportPlan.session_id == uuid.UUID(inp.session_id))
            .order_by(ISImportPlan.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        import_plan = result.scalar_one_or_none()

    if not import_plan:
        return {"phase": inp.phase_id, "status": "error", "error": "Import plan not found."}

    from shared.models.is_models import ISValidationResult

    async with AsyncSessionLocal() as session:
        val_rows = (
            await session.execute(
                select(ISValidationResult)
                .where(ISValidationResult.session_id == uuid.UUID(inp.session_id))
                .limit(50)
            )
        ).scalars().all()
        if any(v.overall_status == "fail" for v in val_rows):
            return {
                "phase": inp.phase_id,
                "status": "error",
                "error": "Validation failed — resolve validate errors before import.",
                "blocked_by": "validation_fail",
            }
        if import_plan.status == "blocked":
            return {
                "phase": inp.phase_id,
                "status": "error",
                "error": "Import plan is blocked — re-validate or upload missing data.",
                "blocked_by": "import_plan_blocked",
            }

    phases = import_plan.phases or {}
    phase_def = phases.get(inp.phase_id)
    if not phase_def:
        return {"phase": inp.phase_id, "status": "error", "error": f"Phase {inp.phase_id} not in plan."}

    steps = phase_def.get("steps", [])

    from shared.erp_policies.submit_gate import (
        all_plan_create_doctypes,
        phase_child_doctypes as _phase_child_doctypes,
    )

    phase_children = _phase_child_doctypes(steps)
    planned_children = all_plan_create_doctypes(phases)
    commit_confidence = await _load_commit_confidence(inp.session_id)
    execution_confirmed = bool(
        inp.execution_confirmed or inp.skip_execution_gate or inp.auto_submit is True
    )
    activity.logger.info(
        "  Submit gate | phase_children=%s planned_children=%s confidence=%.2f execution_confirmed=%s",
        sorted(phase_children),
        sorted(planned_children),
        commit_confidence,
        execution_confirmed,
    )

    s3 = _get_s3_client()
    base_url, adapter = await _resolve_erp_adapter(inp, activity.logger)

    company_ctx: Dict[str, str] = {}

    # ── PRE-FLIGHT BASELINE SEED (before Company / Warehouse creation) ───
    seen_seed_doctypes: set = set()
    seen_seed_values: Dict[str, set] = {}
    if not inp.dry_run and base_url:
        seen_seed_doctypes, seen_seed_values = await _run_baseline_preflight_seed(
            adapter,
            phases,
            activity.logger,
            dry_run=inp.dry_run,
            base_url=base_url,
        )

    # ── SITE PREREQUISITES (Company + Warehouses) ───────────────────────────
    if not inp.dry_run and base_url:
        from containers.implementation.import_agent.site_prerequisites import (
            ensure_site_prerequisites,
        )

        prereq = await ensure_site_prerequisites(
            adapter,
            session_id=inp.session_id,
            company_slug=inp.company_slug or "",
            phases=phases,
            s3=s3,
            link_fields=_KNOWN_LINK_FIELDS,
            logger=activity.logger,
        )
        if prereq.get("company_name"):
            company_ctx["company_name"] = str(prereq["company_name"])
        if prereq.get("company_abbr"):
            company_ctx["company_abbr"] = str(prereq["company_abbr"])
        activity.logger.info(
            "  🏗️  Site prerequisites | company=%s abbr=%s source=%s wh_requested=%s wh_ok=%s wh_failed=%s",
            prereq.get("company_name"),
            prereq.get("company_abbr"),
            prereq.get("company_source"),
            prereq.get("warehouses_requested"),
            prereq.get("warehouses_created"),
            prereq.get("warehouses_failed"),
        )
        if not company_ctx.get("company_name"):
            activity.logger.error(
                "  ❌  Site prerequisites failed — no Company on ERPNext (setup wizard did not succeed)",
            )
            return {
                "phase": inp.phase_id,
                "status": "error",
                "error": (
                    "Site prerequisites failed: could not resolve or create Company on ERPNext. "
                    "Check worker logs for setup wizard errors."
                ),
                "steps_completed": 0,
                "steps_failed": 1,
            }

    # ── EXECUTION GATE (Phase B/C live writes) ─────────────────────────────
    if (
        not inp.dry_run
        and base_url
        and not inp.execution_confirmed
        and not inp.skip_execution_gate
        and inp.phase_id in ("phase_c_transactional", "phase_b_master")
    ):
        from containers.implementation.import_agent.preflight import run_import_preflight

        preflight = await run_import_preflight(
            phase_id=inp.phase_id,
            steps=steps,
            s3=s3,
            adapter=adapter,
            known_link_fields=_KNOWN_LINK_FIELDS,
            log=activity.logger,
        )
        if preflight.get("requires_execution_gate"):
            activity.logger.warning(
                "  ⛔ EXECUTION GATE: confirmation required before %s",
                inp.phase_id,
            )
            return {
                "phase": inp.phase_id,
                "status": "awaiting_confirmation",
                "preflight": preflight,
                "message": preflight.get("confirmation_preview", {}).get("message"),
            }

    # Update plan status
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ISImportPlan)
            .where(ISImportPlan.id == import_plan.id)
            .values(status="executing", current_phase=inp.phase_id)
        )
        await session.commit()

    # ── 2. Execute Steps ─────────────────────────────────────────────────────
    slug = inp.company_slug or "unknown"
    
    execution_logs = []
    total_records_created = 0
    steps_completed = 0
    steps_failed = 0

    activity.logger.info("")
    # ── PASS 2: Dynamic link field discovery ──────────────────────────────
    # Scans import rows for link targets referenced in mapped data only.
    # Automatically creates any missing records in ERPNext before the main
    # import loop runs — preventing LinkValidationError at row-creation time.
    if not inp.dry_run and base_url:
        _name_field_cache: dict = {}
        activity.logger.info("  🔍  PASS 2 — scanning %d step(s) for unknown link targets", len(steps))

        # Build {doctype → set(values)} from all create-action rows in this phase
        _dynamic_link_targets: Dict[str, set] = {}

        for _dyn_step in steps:
            _step_action = _dyn_step.get("action")
            _step_dt = _dyn_step.get("doctype")
            if _step_action != "create":
                activity.logger.info("  🔍    skip step doctype=%s action=%s (not create)", _step_dt, _step_action)
                continue
            activity.logger.info("  🔍    processing step doctype=%s", _step_dt)

            if _dyn_step.get("action") != "create":
                continue
            try:
                _r2_key = _dyn_step.get("data_source")
                _r2_resp = s3.get_object(Bucket="clean-data", Key=_r2_key)
                _payload = json.loads(_r2_resp["Body"].read().decode("utf-8"))
                _rows = _payload.get("records", [])
            except Exception:
                continue

            # Merge global schema index with per-payload link_fields (payload wins).
            # Payloads created before Fix 3 won't have link_fields —
            # _KNOWN_LINK_FIELDS acts as the backward-compatible fallback.
            _payload_link_fields: Dict[str, str] = _payload.get("link_fields", {})
            _effective_link_fields: Dict[str, str] = {**_KNOWN_LINK_FIELDS, **_payload_link_fields}

            for _row in _rows:
                for _field_name, _field_value in _row.items():
                    if not _field_value or not isinstance(_field_value, str):
                        continue
                    _target_dt = _effective_link_fields.get(_field_name)
                    if not _target_dt:
                        continue
                    # Skip if already handled in Pass 1 or blacklisted
                    if _is_seed_blacklisted(_target_dt):
                        continue
                    _val_stripped = _field_value.strip()
                    if _val_stripped in seen_seed_values.get(_target_dt, set()):
                        continue
                    _dynamic_link_targets.setdefault(_target_dt, set()).add(_field_value.strip())


        if _dynamic_link_targets:
            activity.logger.info(
                "  🔍  PASS 2 — Dynamic discovery for %d unknown doctype(s): %s",
                len(_dynamic_link_targets),
                ", ".join(_dynamic_link_targets.keys()),
            )
            for _dyn_dt, _dyn_vals in _dynamic_link_targets.items():
                _counts = await _dynamic_seed_doctype(
                    _dyn_dt, list(_dyn_vals), adapter,
                    _name_field_cache, activity.logger,
                )
                activity.logger.info(
                    "  🔍  %-22s  seeded=%d  already_existed=%d  failed=%d",
                    _dyn_dt, _counts["seeded"], _counts["already"], _counts["failed"],
                )
        else:
            activity.logger.info("  🔍  PASS 2 — No unknown link targets found, skipping")

    activity.logger.info("")
    # ── END PASS 2 ────────────────────────────────────────────────────────

    # ── PASS 2.5: Bulk link pre-resolution ────────────────────────────────
    _pre_resolved_cache: Dict[str, List[Dict]] = {}
    _step_resolution_summaries: Dict[str, Dict[str, Any]] = {}

    if not inp.dry_run and base_url:
        activity.logger.info("  🔗  PASS 2.5 — Bulk link pre-resolution")
        _pre_resolved_cache, _step_resolution_summaries = await _bulk_pre_resolve_phase_rows(
            steps,
            s3,
            adapter,
            _KNOWN_LINK_FIELDS,
            activity.logger,
            company_abbr=company_ctx.get("company_abbr", ""),
        )
        activity.logger.info("")
    # ── END PASS 2.5 ─────────────────────────────────────────────────────

    for step_idx, step in enumerate(steps):
        dt = step.get("doctype", "")
        action = step.get("action", "")
        step_start = datetime.utcnow()

        # Skip actions that are not row-level imports
        if action in ("default_or_skip", "skip", "seed_from_baseline", "data_gap", "optional_skip"):
            if action == "data_gap":
                activity.logger.warning(
                    "  ⚠️  DATA GAP: %s has no mapped data file and no baseline — skipping", dt
                )
            elif action == "optional_skip":
                activity.logger.info(
                    "  ⏭️  OPTIONAL SKIP: %s deferred (important but not critical for this import)", dt
                )
            continue

        if action == "auto_from_company":
            activity.logger.info(
                "  ⏭️  %s auto-created by ERPNext on Company setup — skipping", dt
            )
            steps_completed += 1
            continue

        if action in ("discover_from_site", "auto_company_setup"):
            if not inp.dry_run and base_url:
                from containers.implementation.import_agent.site_prerequisites import (
                    discover_fiscal_year_exists,
                    resolve_company_for_import,
                    collect_warehouse_names,
                )
                if dt == "Company":
                    wh_names = collect_warehouse_names(phases, s3, _KNOWN_LINK_FIELDS)
                    resolved = await resolve_company_for_import(
                        adapter,
                        session_id=inp.session_id,
                        company_slug=inp.company_slug or "",
                        warehouse_names=wh_names,
                        logger=activity.logger,
                    )
                    if resolved:
                        company_ctx["company_name"] = resolved["name"]
                        if resolved.get("abbr"):
                            company_ctx["company_abbr"] = resolved["abbr"]
                elif dt == "Fiscal Year":
                    if await discover_fiscal_year_exists(adapter, activity.logger):
                        activity.logger.info(
                            "  📅  Fiscal Year exists on live site (from onboarding) — skipping"
                        )
                    else:
                        try:
                            await adapter.seed_from_config(dt, {})
                        except Exception as e:
                            activity.logger.warning(
                                "  ⚠️  Fiscal Year seed skipped/failed: %s", e
                            )
            activity.logger.info("  🏢  discover_from_site for %s — handled", dt)
            steps_completed += 1
            continue

        if action == "seed_from_config":
            project_details = {}
            if inp.project_id:
                try:
                    from shared.models.core import Project
                    async with AsyncSessionLocal() as db:
                        stmt = select(Project).where(Project.id == uuid.UUID(inp.project_id))
                        res = await db.execute(stmt)
                        project = res.scalar_one_or_none()
                        if project and project.deployment_details:
                            project_details = dict(project.deployment_details)
                except Exception as e:
                    activity.logger.warning("  ⚠️ Failed to read project details: %s", e)

            if not company_ctx:
                from containers.implementation.import_agent.site_prerequisites import (
                    collect_warehouse_names,
                    load_company_context,
                )
                company_ctx = await load_company_context(
                    inp.session_id, inp.company_slug or "",
                )
            if company_ctx.get("company_name"):
                project_details["company_name"] = company_ctx["company_name"]
            if dt == "Warehouse":
                project_details["warehouse_names"] = sorted(
                    collect_warehouse_names(phases, s3, _KNOWN_LINK_FIELDS)
                )

            if not inp.dry_run and base_url:
                try:
                    await adapter.seed_from_config(dt, project_details)
                    activity.logger.info("  🌱  Executed seed_from_config for %s successfully", dt)
                except Exception as e:
                    activity.logger.error("  ❌ Failed to execute seed_from_config for %s: %s", dt, e)
            continue

        # Download payload from R2 (prefer Pass 2.5 pre-resolved cache)
        rows = []
        r2_key = step.get("data_source")
        try:
            if r2_key and r2_key in _pre_resolved_cache:
                rows = [dict(r) for r in _pre_resolved_cache[r2_key]]
            else:
                response = s3.get_object(Bucket="clean-data", Key=r2_key)
                payload = json.loads(response["Body"].read().decode("utf-8"))
                rows = payload.get("records", [])
        except Exception:
            activity.logger.warning("  No R2 data found for %s — skipping", dt)
            continue

        resolution_summary = _step_resolution_summaries.get(r2_key, {}) if r2_key else {}
        submit_summary: List[dict] = []

        records_attempted = len(rows)
        records_succeeded = 0
        records_failed = 0
        error_details = []
        erpnext_responses = []

        # Dry Run vs Live
        if inp.dry_run or not base_url:
            records_succeeded = records_attempted
            steps_completed += 1
            status = "success"
            erpnext_responses = ["DRY_RUN_MOCK_SUCCESS"] * records_succeeded
            submit_summary = []
        else:
            # 🚀 LIVE IMPORT: Row-by-Row via ERPAdapter
            from shared.erp_adapters.import_idempotency import find_existing_record

            submit_summary = []
            for row_idx, row in enumerate(rows):
                # ── Runtime normalization: fix known invalid Select values ──
                row = dict(row)  # shallow copy — don't mutate original
                if dt == "Supplier":
                    _stype = row.get("supplier_type", "")
                    if _stype not in ("Company", "Individual", "Partnership"):
                        row["supplier_type"] = "Company"
                if dt == "Customer":
                    _ctype = row.get("customer_type", "")
                    if _ctype not in ("Company", "Individual", "Partnership"):
                        row["customer_type"] = "Company"
                if dt in _COMPANY_REQUIRED_DOCTYPES and not row.get("company"):
                    _cname = company_ctx.get("company_name")
                    if _cname:
                        row["company"] = _cname
                # ────────────────────────────────────────────────────────────
                try:
                    existing_doc = await find_existing_record(adapter, dt, row)
                    if existing_doc:
                        activity.logger.info(
                            "  ♻️  Idempotent skip %s row %d → existing '%s'",
                            dt,
                            row_idx,
                            existing_doc.get("name"),
                        )
                        data = existing_doc
                    else:
                        data = await adapter.create_record(dt, row)

                    records_succeeded += 1
                    erpnext_responses.append(data)

                    submit_entry = await _submit_after_create_if_needed(
                        adapter,
                        dt,
                        data if isinstance(data, dict) else {},
                        auto_submit_override=inp.auto_submit,
                        commit_confidence=commit_confidence,
                        phase_child_doctypes=planned_children,
                        execution_confirmed=execution_confirmed,
                        logger=activity.logger,
                    )
                    if submit_entry:
                        submit_summary.append(submit_entry)

                except ValueError as exc:
                    # Adapter raises ValueError for 4xx errors (including duplicates)
                    err_msg = str(exc)
                    if "already exist" in err_msg.lower() or "duplicate" in err_msg.lower():
                        records_succeeded += 1
                        existing = await find_existing_record(adapter, dt, row) or {
                            "_status": "already_exists",
                        }
                        erpnext_responses.append(existing)
                        submit_entry = await _submit_after_create_if_needed(
                            adapter,
                            dt,
                            existing,
                            auto_submit_override=inp.auto_submit,
                            commit_confidence=commit_confidence,
                            phase_child_doctypes=planned_children,
                            execution_confirmed=execution_confirmed,
                            logger=activity.logger,
                        )
                        if submit_entry:
                            submit_summary.append(submit_entry)
                    else:
                        records_failed += 1
                        error_details.append({"row_index": row_idx, "error": err_msg})
                        activity.logger.error("  ❌ ERPNext API Error on %s row %d: %s", dt, row_idx, err_msg)

                except Exception as exc:
                    records_failed += 1
                    err_msg = str(exc)
                    error_details.append({"row_index": row_idx, "error": err_msg})
                    activity.logger.error("  ❌ ERPNext API Error on %s row %d: %s", dt, row_idx, err_msg)

            status = "failed" if records_failed > 0 else "success"
            if records_failed > 0:
                steps_failed += 1
            else:
                steps_completed += 1

        total_records_created += records_succeeded
        duration_sec = (datetime.utcnow() - step_start).total_seconds()

        # Build Log Object
        log_entry = {
            "step": step_idx + 1,
            "doctype": dt,
            "status": status,
            "records_attempted": records_attempted,
            "records_succeeded": records_succeeded,
            "records_failed": records_failed,
            "duration_seconds": int(duration_sec),
            "resolution_summary": resolution_summary,
            "submit_summary": {
                "submitted_count": sum(1 for s in submit_summary if s.get("action") == "submitted"),
                "actions": submit_summary,
            },
        }
        execution_logs.append(log_entry)

        # Persist to Supabase ISImportLog
        async with AsyncSessionLocal() as db_session:
            db_session.add(ISImportLog(
                id=uuid.uuid4(),
                import_plan_id=import_plan.id,
                phase=inp.phase_id,
                step_number=step_idx + 1,
                doctype=dt,
                action=action,
                status=status,
                records_attempted=records_attempted,
                records_succeeded=records_succeeded,
                records_failed=records_failed,
                error_message="Import errors occurred" if records_failed > 0 else None,
                error_details=json.dumps(error_details) if error_details else None,
                erpnext_response=json.dumps(erpnext_responses[:5]) if erpnext_responses else None, # Save first 5 responses for auditing
                started_at=step_start,
                completed_at=datetime.utcnow(),
                duration_seconds=int(duration_sec)
            ))
            await db_session.commit()

    # ── 3. Update import plan status ─────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ISImportPlan)
            .where(ISImportPlan.id == import_plan.id)
            .values(
                current_phase=inp.phase_id,
                current_step=len(steps),
            )
        )
        await session.commit()

    # ── 4. Audit trail ───────────────────────────────────────────────────────
    phase_status = "error" if steps_failed > 0 else "success"
    try:
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="import_executed",
            actor="system",
            entity_type="import",
            details={
                "phase": inp.phase_id, 
                "steps_completed": steps_completed, 
                "records_created": total_records_created
            },
            result=phase_status,
        )
    except Exception:
        pass

    activity.logger.info("✅ execute_import_phase done | phase=%s records=%d", inp.phase_id, total_records_created)
    
    # ── 5. Return Output per Blueprint ───────────────────────────────────────
    return {
        "phase": inp.phase_id,
        "status": phase_status,
        "steps_completed": steps_completed,
        "steps_failed": steps_failed,
        "records_created": total_records_created,
        "execution_logs": execution_logs
    }