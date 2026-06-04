"""
Mapping Agent — Temporal activities for mapping uploaded files to ERPNext doctypes.

Activities download file content from R2, process it, upload results to R2,
and persist metadata to Supabase. Temporal only sees tiny string returns.
"""
from __future__ import annotations

import csv
import io
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity
from sqlalchemy import select, update, delete

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import (
    ISCompanyProfile,
    ISFieldMapping,
    ISFieldMappingHistory,
    ISMappedData,
    ISSession,
)
from containers.implementation.is_common.doctype_resolver import resolve_doctype
from shared.models.is_status import NodeStatusEnvelope
from containers.implementation.utils.llm_helper import generate_json

# 🚀 Importing the prompt cleanly!
from containers.implementation.mapping_agent.prompts import REFINE_MAPPING_PROMPT
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings
from containers.implementation.mapping_agent.classifier import classify_doctype
from containers.implementation.mapping_agent.extraction import (
    extract_unstructured_records,
    validate_records_against_schema,
)
from containers.implementation.mapping_agent.defaults import (
    fold_child_tables,
    apply_defaults_and_normalize,
)
from containers.implementation.mapping_agent.corpus_merge import (
    filename_conflicts_with_doctype,
    filename_implied_doctype,
    filter_quarantined_records,
    load_r2_json,
    merge_extracted_rows,
    merge_payloads,
)

FIELD_MAPPINGS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "knowledge_base" / "erpnext" / "schema" / "field_mappings.json"
)

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

class _MappingEngine:
    def __init__(self):
        self._field_mappings: Dict = {}

    def _load_field_mappings(self) -> Dict:
        # Prefer cached KB loader to keep reads deterministic and fast.
        if not self._field_mappings:
            self._field_mappings = _kb_field_mappings() or {}
        return self._field_mappings

    def infer_doctype(self, columns: List[str], sample_text: Optional[str] = None) -> Optional[str]:
        """Infer the best-matching ERPNext doctype using weighted synonym scoring."""
        if columns and len(columns) > 1:
            cols_lower = [c.lower().strip() for c in columns if c is not None]
            data = self._load_field_mappings()
            mappings = data.get("doctypes", {})

            scores: Dict[str, float] = {}
            for doctype, config in mappings.items():
                field_mappings = config.get("field_mappings", {})
                score = 0.0
                for field, fconfig in field_mappings.items():
                    synonyms = list(fconfig.get("user_input_synonyms", []))
                    synonyms.append(fconfig.get("fieldname", field))

                    for syn in synonyms:
                        syn_lower = syn.lower().strip()
                        for c in cols_lower:
                            if c == syn_lower:
                                score += 3.0  # Exact match
                                break
                            elif syn_lower in c and len(syn_lower) >= 3:
                                # Synonym is substring of column: only score if it's a significant portion
                                if len(syn_lower) / max(len(c), 1) >= 0.5:
                                    score += 2.0
                                else:
                                    score += 0.3  # Very weak partial
                                break
                            elif c in syn_lower and len(c) >= 4:
                                # Column is substring of synonym: only if column is significant portion
                                if len(c) / max(len(syn_lower), 1) >= 0.5:
                                    score += 0.5
                                break

                if score >= 4.0:
                    scores[doctype] = score

            if scores:
                best = max(scores, key=scores.get)
                activity.logger.info("  Doctype inference scores: %s → best=%s (%.1f)",
                                     {k: round(v, 1) for k, v in sorted(scores.items(), key=lambda x: -x[1])[:5]},
                                     best, scores[best])
                return best

        # Fallback to LLM inference
        data = self._load_field_mappings()
        available_doctypes = list(data.get("doctypes", {}).keys())
        
        prompt = "You are an ERP data specialist. "
        if columns and len(columns) > 1:
            prompt += f"I have a tabular file with columns: {columns}. "
        elif sample_text:
            prompt += f"I have an unstructured text file. Here is a snippet of the content:\n\n{sample_text[:1000]}\n\n"
        else:
            return None
            
        prompt += f"Based on this information, infer matching ERPNext doctype from this exact list: {available_doctypes}. "
        prompt += 'Return JSON: {"doctype": "Exact Doctype Name"}. If there is absolutely no match, return {"doctype": null}.'
        
        try:
            res = generate_json(prompt, max_output_tokens=1000)
            return res.get("doctype")
        except Exception as e:
            return None

    # ── PROTOCOL-COMPLIANT: Entity synonyms are read from field_mappings.json ──
    # 'party_type_synonyms' key maps canonical names → list of user-facing aliases.
    # Fallback to old hardcoded set if the key is absent from the JSON.
    # ──────────────────────────────────────────────────────────────────────────

    # Fallback: used only if field_mappings.json lacks 'party_type_synonyms'
    _ENTITY_TYPE_VALUES_FALLBACK = {"supplier", "customer", "vendor", "client", "buyer", "seller"}

    def _get_party_type_synonyms(self) -> Dict[str, List[str]]:
        """Load party_type_synonyms from field_mappings.json.
        Returns { 'Customer': ['client', 'buyer', ...], 'Supplier': [...] }.
        Falls back to a minimal hardcoded dict if not present in JSON.
        """
        data = self._load_field_mappings()
        synonyms = data.get("party_type_synonyms")
        if isinstance(synonyms, dict) and synonyms:
            # Support both shapes:
            # - {alias: canonical} from the KB JSON
            # - {canonical: [aliases]} from older runtime expectations
            normalized: Dict[str, List[str]] = {}
            if all(isinstance(v, str) for v in synonyms.values()):
                for alias, canonical in synonyms.items():
                    canonical_name = str(canonical).strip()
                    alias_name = str(alias).strip().lower()
                    if not canonical_name:
                        continue
                    normalized.setdefault(canonical_name, [])
                    if alias_name and alias_name not in normalized[canonical_name]:
                        normalized[canonical_name].append(alias_name)
            else:
                for canonical, aliases in synonyms.items():
                    canonical_name = str(canonical).strip()
                    if not canonical_name:
                        continue
                    normalized.setdefault(canonical_name, [])
                    for alias in aliases or []:
                        alias_name = str(alias).strip().lower()
                        if alias_name and alias_name not in normalized[canonical_name]:
                            normalized[canonical_name].append(alias_name)
            for canonical_name, aliases in normalized.items():
                canonical_alias = canonical_name.lower()
                if canonical_alias not in aliases:
                    aliases.append(canonical_alias)
            return normalized
        # Fallback: replicate old hardcoded behaviour
        return {
            "Customer": ["customer", "client", "buyer"],
            "Supplier": ["supplier", "vendor", "seller"],
        }

    def _split_by_entity_type(self, rows: List[Dict], columns: List[str]) -> Optional[Dict[str, List[Dict]]]:
        """
        Detect if a file contains multiple entity types (e.g., Suppliers AND Customers)
        and split rows by their Type column into separate groups.

        Only splits if the Type column actually contains party-type values
        (Customer/Supplier/Vendor/Client), NOT item-type values (Raw Material/Finished Good).

        Returns None if no split is needed, or {entity_type: [rows]} if split applies.
        """
        # Build synonym index from JSON (or fallback)
        party_synonyms = self._get_party_type_synonyms()
        # Flat set of all known alias values for quick membership testing
        all_entity_aliases: set = {alias for aliases in party_synonyms.values() for alias in aliases}
        # Reverse map: lowercase alias → canonical name
        alias_to_canonical: Dict[str, str] = {
            alias: canonical
            for canonical, aliases in party_synonyms.items()
            for alias in aliases
        }

        type_col = None
        type_synonyms = {"type", "entity type", "entity_type", "record type", "party type", "party_type"}
        for c in columns:
            normalized_column = c.lower().strip().replace("_", " ")
            if c and (normalized_column in type_synonyms or c.lower().strip() in type_synonyms):
                type_col = c
                break

        if not type_col:
            return None

        # Validate: check if the values in this column are actually entity types
        unique_values = set()
        for row in rows:
            raw_type = (row.get(type_col) or "").strip().lower()
            if raw_type:
                unique_values.add(raw_type)

        # Only split if at least 30% of unique values match known entity types
        if not unique_values:
            return None
        entity_match_count = sum(1 for v in unique_values if v in all_entity_aliases)
        if entity_match_count / len(unique_values) < 0.3:
            activity.logger.info("  Type column '%s' has non-entity values %s — skipping split",
                                 type_col, unique_values)
            return None

        groups: Dict[str, List[Dict]] = {}
        for row in rows:
            raw_type = (row.get(type_col) or "").strip()
            if not raw_type:
                continue
            # Normalize via JSON alias map; if unknown, keep as-is
            normalized = alias_to_canonical.get(raw_type.lower(), raw_type)
            groups.setdefault(normalized, []).append(row)

        # Only split if we have ≥2 distinct entity types
        if len(groups) >= 2:
            activity.logger.info("  Multi-entity split detected: %s", {k: len(v) for k, v in groups.items()})
            return groups

        return None

    def map_columns(self, columns: List[str], doctype: Optional[str] = None, sample_row: Optional[Dict] = None) -> Dict[str, str]:
        if not doctype:
            doctype = self.infer_doctype(columns)
        if not doctype:
            return {}
            
        data = self._load_field_mappings()
        config = data.get("doctypes", {}).get(doctype, {})
        field_mappings = config.get("field_mappings", {})
        
        result: Dict[str, str] = {}
        unmapped_cols = []

        def _col_matches_synonym(col_l: str, synonym: str) -> bool:
            """
            True when the column name is an exact or equivalent match for the synonym.
            Uses exact equality only — NOT substring — so that a column named
            "child_item_code" doesn't accidentally match the synonym "item".
            """
            syn_l = synonym.lower().strip()
            if not syn_l:
                return False
            # Exact match (covers both identical and normalised variants)
            if col_l == syn_l:
                return True
            # Normalise underscores ↔ spaces (e.g. "item code" == "item_code")
            if col_l.replace(" ", "_") == syn_l.replace(" ", "_"):
                return True
            return False
        
        for col in columns:
            if col is None:
                continue
            col_lower = col.lower().strip()
            matched = False

            # Pass 1: match against top-level fields (exact/token match only).
            for field, fconfig in field_mappings.items():
                synonyms = list(fconfig.get("user_input_synonyms", []))
                erp_fieldname = fconfig.get("fieldname", field)
                synonyms.append(erp_fieldname)
                
                if any(_col_matches_synonym(col_lower, syn) for syn in synonyms):
                    result[col] = erp_fieldname
                    matched = True
                    break

            if matched:
                continue

            # Pass 2: match against child_fields inside Table entries.
            # Child synonyms are specific (e.g., "child_item_code") so the original
            # relaxed substring match is safe here.
            # When found, store as "<table_fieldname>.<child_fieldname>" so
            # fold_child_tables can later peel this apart correctly.
            for field, fconfig in field_mappings.items():
                if str(fconfig.get("fieldtype") or "").strip().lower() != "table":
                    continue
                table_fieldname = fconfig.get("fieldname", field)
                child_fields = fconfig.get("child_fields") or {}
                for child_key, cfcfg in child_fields.items():
                    child_synonyms = list(cfcfg.get("user_input_synonyms") or [])
                    child_erp_fieldname = cfcfg.get("fieldname", child_key)
                    child_synonyms.append(child_erp_fieldname)
                    if any(syn.lower() in col_lower or col_lower in syn.lower() for syn in child_synonyms):
                        result[col] = f"{table_fieldname}.{child_erp_fieldname}"
                        matched = True
                        break
                if matched:
                    break

            if not matched:
                unmapped_cols.append(col)
                
        # NOTE (Determinism): We intentionally do NOT use LLM-based column mapping here.
        # LLM column mapping is non-deterministic and caused schema drift. Unmapped
        # columns are ignored; defaults + schema-locked extraction cover gaps.
                
        return result

    def _keyword_infer_doctype(self, content: str) -> Optional[str]:
        """Keyword-based fallback doctype inference for unstructured text when LLM fails.

        Reads 'doctype_keyword_hints' from field_mappings.json.
        Each entry: { "keywords": [...], "min_score": N }.
        Falls back to hardcoded Company/Employee rules if the key is absent.
        """
        text_lower = content.lower()
        data = self._load_field_mappings()
        hints = data.get("doctype_keyword_hints")

        if hints:
            # JSON-driven: score every doctype, pick highest above threshold
            best_doctype, best_score = None, 0
            for doctype, cfg in hints.items():
                score = sum(1 for kw in cfg.get("keywords", []) if kw.lower() in text_lower)
                min_score = cfg.get("min_score", 3)
                if score >= min_score and score > best_score:
                    best_score, best_doctype = score, doctype
            return best_doctype

        # Fallback: original hardcoded rules (preserved for backward compatibility)
        company_keywords = ["gstin", "gst", "company", "pvt", "ltd", "currency", "inr", "bank", "branch"]
        company_score = sum(1 for kw in company_keywords if kw in text_lower)
        if company_score >= 3:
            return "Company"
        emp_keywords = ["employee", "staff", "designation", "department", "joining", "salary"]
        if sum(1 for kw in emp_keywords if kw in text_lower) >= 3:
            return "Employee"
        return None

    def _extract_nlp_rows(self, content: str, doctype: str) -> List[Dict]:
        data = self._load_field_mappings()
        field_mappings = data.get("doctypes", {}).get(doctype, {}).get("field_mappings", {})
        
        parent_schema = {k: v.get("fieldname", k) for k, v in field_mappings.items() if v.get("fieldtype") != "Table"}
        child_tables = {v.get("fieldname", k): v.get("child_fields", {}) for k, v in field_mappings.items() if v.get("fieldtype") == "Table"}

        prompt1 = f"I have unstructured text that represents records for an ERPNext '{doctype}'.\n"
        prompt1 += f"Extract the parent-level data into a structured array of JSON objects.\n"
        prompt1 += f"Each object should ONLY contain keys from this exact parent schema: {list(parent_schema.values())}\n"
        prompt1 += "CRITICAL: For any date fields (e.g., delivery_date, transaction_date), you MUST use a strict JSON schema where the field is 'type: string, format: date'. Convert all dates strictly to 'YYYY-MM-DD' (e.g., convert 'Next Monday' to a valid YYYY-MM-DD date).\n"
        prompt1 += f"Do not invent fields. Do not extract child table items in this step.\n"
        prompt1 += f"Here is the text to parse:\n\n{content[:4000]}\n\n"
        prompt1 += 'Return JSON: { "rows": [ {"field1": "val", "delivery_date": "YYYY-MM-DD"} ] }'
        
        try:
            res1 = generate_json(prompt1, max_output_tokens=4000)
            parent_rows = res1.get("rows", [])
        except Exception:
            return []
            
        if not parent_rows:
            return []

        # Call 2: Extract child data
        if child_tables:
            for parent_row in parent_rows:
                for child_fieldname, child_schema in child_tables.items():
                    child_keys = [v.get("fieldname", k) for k, v in child_schema.items()]
                    prompt2 = f"I have unstructured text that represents a record for an ERPNext '{doctype}'.\n"
                    prompt2 += f"The parent document details are: {json.dumps(parent_row)}\n"
                    prompt2 += f"Extract ALL line items, services, or materials mentioned in this text related to this parent document into an array of objects.\n"
                    prompt2 += f"Each object should ONLY contain keys from this exact child schema: {child_keys}\n"
                    prompt2 += f"For items, ensure you extract standard 'item_code', 'qty', and 'rate' values. Convert casual expenses into valid ERP items.\n"
                    prompt2 += f"Here is the text to parse:\n\n{content[:4000]}\n\n"
                    prompt2 += 'Return JSON: { "child_items": [ {"item_code": "val", "qty": 1, "rate": 10.0} ] }'
                    
                    try:
                        res2 = generate_json(prompt2, max_output_tokens=4000)
                        parent_row[child_fieldname] = res2.get("child_items", [])
                    except Exception:
                        parent_row[child_fieldname] = []
                        
        return parent_rows

    def map_file(self, content: str, filename: str, doctype_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Map a single file to one or more ERPNext doctypes.
        
        Returns a LIST of mapping results (one per doctype) to support multi-entity files.
        Each result dict has: doctype, field_mapping, rows, inferred_doctype, source_columns.
        """
        is_unstructured = filename.lower().endswith(".txt") or filename.lower().endswith(".pdf")
        
        if is_unstructured:
            doctype = doctype_hint or self.infer_doctype([], sample_text=content)
            # Keyword-based fallback when LLM fails for unstructured files
            if not doctype:
                doctype = self._keyword_infer_doctype(content)
            if not doctype:
                return [{"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None, "source_columns": []}]
            rows = self._extract_nlp_rows(content, doctype)
            if not rows:
                return [{"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None, "source_columns": []}]
                
            columns = list(rows[0].keys())
            return [{
                "doctype": doctype,
                "field_mapping": {c: c for c in columns}, 
                "rows": rows,
                "inferred_doctype": doctype,
                "source_columns": columns,
            }]
        else:
            rows = list(csv.DictReader(io.StringIO(content)))
            clean_rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
            if not clean_rows:
                return [{"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None, "source_columns": []}]
                
            columns = [c for c in list(clean_rows[0].keys()) if c is not None]

            # ── CHECK FOR MULTI-ENTITY FILE ──
            split_groups = self._split_by_entity_type(clean_rows, columns)
            if split_groups:
                results = []
                for entity_type, group_rows in split_groups.items():
                    # FIRST: Try direct entity-name-to-doctype match (highest priority)
                    group_doctype = None
                    data = self._load_field_mappings()
                    for dt_name in data.get("doctypes", {}).keys():
                        if entity_type.lower() == dt_name.lower():
                            group_doctype = dt_name
                            break
                    
                    # SECOND: Fall back to column-based inference if no direct match
                    if not group_doctype:
                        group_doctype = self.infer_doctype(columns, sample_text=entity_type)
                    
                    if not group_doctype:
                        group_doctype = entity_type  # Use entity_type as-is
                    
                    field_mapping = self.map_columns(columns, group_doctype, sample_row=group_rows[0])
                    results.append({
                        "doctype": group_doctype,
                        "field_mapping": field_mapping,
                        "rows": group_rows,
                        "inferred_doctype": group_doctype,
                        "source_columns": columns,
                    })
                return results
            
            # ── SINGLE DOCTYPE MAPPING ──
            doctype = doctype_hint or self.infer_doctype(columns)
            field_mapping = self.map_columns(columns, doctype, sample_row=clean_rows[0])
            
            return [{
                "doctype": doctype,
                "field_mapping": field_mapping,
                "rows": clean_rows,
                "inferred_doctype": doctype,
                "source_columns": columns,
            }]

# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class MapFileInput:
    r2_manifest_url: str 
    filename: str
    project_id: str
    company_slug: str
    session_id: str
    doctype_hint: Optional[str] = None
    corpus_assignment: Optional[Dict[str, Any]] = None
    retry_feedback: Optional[str] = None


async def _load_session_required_doctypes(session_id: str) -> List[str]:
    """
    Load the most recent ISTargetStructure.required_doctypes for the session.
    Returns [] on any failure.
    """
    try:
        from shared.models.is_models import ISTargetStructure
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISTargetStructure)
                .where(ISTargetStructure.session_id == uuid.UUID(session_id))
                .order_by(ISTargetStructure.created_at.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()
            if not row or not row.required_doctypes:
                return []
            required = row.required_doctypes
            if isinstance(required, str):
                try:
                    required = json.loads(required)
                except Exception:
                    required = []
            if not isinstance(required, list):
                return []
            return [str(x) for x in required if x]
    except Exception:
        return []


async def _load_session_context(session_id: str) -> Dict[str, Any]:
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(ISSession).where(ISSession.id == uuid.UUID(session_id))
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()
            ctx: Dict[str, Any] = {}
            if row:
                ctx = {
                    "user_import_note": row.user_import_note or "",
                    "file_batches": row.file_batches or [],
                    "user_notes": row.user_notes or [],
                }
            prof_stmt = (
                select(ISCompanyProfile.company_name)
                .where(ISCompanyProfile.session_id == uuid.UUID(session_id))
                .order_by(ISCompanyProfile.version.desc())
                .limit(1)
            )
            prof_res = await session.execute(prof_stmt)
            company_name = prof_res.scalar_one_or_none()
            if company_name:
                ctx["company_name"] = str(company_name)
            return ctx
    except Exception:
        return {}


def _defaults_context(
    session_context: Dict[str, Any],
    *,
    company_slug: Optional[str] = None,
) -> Dict[str, Any]:
    company = (session_context or {}).get("company_name") or ""
    if not company and company_slug and company_slug not in ("unknown", ""):
        company = company_slug.replace("-", " ").replace("_", " ").title()
    return {"company_name": company} if company else {}


async def _get_candidate_doctypes(session_id: str) -> List[str]:
    """
    Best-practice candidate list for deterministic routing.

    - Prefer session-scoped ISTargetStructure.required_doctypes
    - Always include a small safe core set
    """
    core = {
        "Item",
        "Customer",
        "Supplier",
        "Employee",
        "Sales Order",
        "Purchase Order",
        "Project",
        "BOM",
        "Work Order",
        "Stock Entry",
        "Purchase Receipt",
        "Delivery Note",
    }
    kb = _kb_field_mappings() or {}
    kb_doctypes = set((kb.get("doctypes") or {}).keys())
    required = set(await _load_session_required_doctypes(session_id))

    candidates = set()
    if required:
        # Do NOT intersect with kb_doctypes! The live_schema engine handles KB misses dynamically.
        candidates |= required
    candidates |= (core & kb_doctypes) if kb_doctypes else core

    # Stable order for determinism: sort case-insensitively but keep original
    return sorted(candidates, key=lambda s: s.lower())

@dataclass
class MapColumnsInput:
    columns: List[str]
    doctype_hint: Optional[str] = None

@dataclass
class RefineMappingInput:
    session_id: str
    user_feedback: str
    project_id: str
    company_slug: str = "unknown"

@dataclass
class AssignCorpusDoctypesInput:
    session_id: str
    project_id: str
    r2_manifest_url: str
    company_slug: str = "unknown"

async def _should_map_doctype(
    session_id: str,
    doctype: str,
    *,
    from_party_split: bool = False,
    filename: Optional[str] = None,
) -> bool:
    """Check whether mapping should proceed for this doctype.

    Prefer import-plan actions of create/pending_mapping. When the blueprint plan
    still shows data_gap (built before mapping), fall back to target structure and
    readiness assessment so uploaded files can be mapped on first pass.

    Party-split groups always map when corpus rules require it.
    Strong filename priors can bypass a negative plan decision.
    """
    from containers.implementation.is_common.doctype_resolver import (
        contains_doctype,
        resolve_doctype,
    )

    doctype = resolve_doctype(doctype)

    if from_party_split:
        from containers.knowledge_base.erpnext.schema.compose import corpus_rules

        if corpus_rules().get("always_map_split_entities"):
            return True

    if filename:
        from containers.implementation.mapping_agent.corpus_merge import filename_implied_doctype

        implied = filename_implied_doctype(filename)
        if implied and resolve_doctype(implied) == doctype:
            return True

    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISImportPlan, ISTargetStructure, ISDataReadinessAssessment
    from sqlalchemy import select
    import uuid

    def _step_matches(step: dict) -> bool:
        step_dt = resolve_doctype(step.get("doctype") or "")
        return step_dt == doctype or resolve_doctype(step.get("doctype") or "") == doctype

    try:
        async with AsyncSessionLocal() as session:
            plan_action: Optional[str] = None
            stmt = (
                select(ISImportPlan)
                .where(ISImportPlan.session_id == uuid.UUID(session_id))
                .order_by(ISImportPlan.created_at.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            plan = res.scalar_one_or_none()
            if plan and plan.phases:
                for phase_data in plan.phases.values():
                    for step in phase_data.get("steps", []):
                        if _step_matches(step):
                            plan_action = step.get("action")
                            break
                    if plan_action is not None:
                        break
                if plan_action in ("create", "pending_mapping"):
                    return True
                if plan_action not in (None, "data_gap"):
                    return False

            target_stmt = (
                select(ISTargetStructure)
                .where(ISTargetStructure.session_id == uuid.UUID(session_id))
                .order_by(ISTargetStructure.created_at.desc())
                .limit(1)
            )
            target_res = await session.execute(target_stmt)
            target = target_res.scalar_one_or_none()
            if target:
                setup_steps = target.setup_steps
                if isinstance(setup_steps, str):
                    try:
                        setup_steps = json.loads(setup_steps)
                    except Exception:
                        setup_steps = []
                required_raw: List[str] = []
                if isinstance(setup_steps, list):
                    for step in setup_steps:
                        if not isinstance(step, dict):
                            continue
                        step_dt = resolve_doctype(step.get("doctype") or "")
                        if step_dt != doctype:
                            continue
                        action = step.get("action") or step.get("planner_action") or ""
                        if action in ("create", "pending_mapping", "must_create"):
                            return True
                    required = target.required_doctypes
                    if isinstance(required, str):
                        try:
                            required = json.loads(required)
                        except Exception:
                            required = []
                    if isinstance(required, list):
                        required_raw = [resolve_doctype(str(x)) for x in required]
                        if contains_doctype(required_raw, doctype):
                            return True

            readiness_stmt = (
                select(ISDataReadinessAssessment)
                .where(ISDataReadinessAssessment.session_id == uuid.UUID(session_id))
                .order_by(ISDataReadinessAssessment.created_at.desc())
                .limit(1)
            )
            readiness_res = await session.execute(readiness_stmt)
            readiness = readiness_res.scalar_one_or_none()
            if readiness:
                for item in (readiness.ready_doctypes or []) + (readiness.partial_doctypes or []):
                    dt_name = item.get("doctype") if isinstance(item, dict) else (item.doctype if hasattr(item, "doctype") else item)
                    if resolve_doctype(str(dt_name or "")) == doctype:
                        return True
                gap_report = readiness.gap_report or {}
                for bucket in ("ready_doctypes", "partial_doctypes"):
                    for item in gap_report.get(bucket, []) or []:
                        if isinstance(item, dict) and resolve_doctype(item.get("doctype") or "") == doctype:
                            return True
            return False
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not check import plan: %s", e)
        return True


# ── Activity definitions ─────────────────────────────────────────────────────
@activity.defn(name="assign_corpus_doctypes")
async def assign_corpus_doctypes(inp: AssignCorpusDoctypesInput) -> Any:
    activity.logger.info("▶ assign_corpus_doctypes started | session=%s manifest=%s", inp.session_id, inp.r2_manifest_url)

    s3 = _get_s3_client()
    session_context = await _load_session_context(inp.session_id)

    try:
        response = s3.get_object(Bucket="clean-data", Key=inp.r2_manifest_url)
        raw = response["Body"].read()
        manifest = json.loads(raw.decode("utf-8"))
    except Exception as e:
        activity.logger.error("❌ Failed to download manifest for corpus assignment: %s", e)
        return NodeStatusEnvelope.failed(
            errors=[{"code": "MANIFEST_DOWNLOAD_FAILED", "message": "Failed to download manifest from R2", "details": {"error": str(e)}}],
            primary_result={"assignments": []},
        )

    engine = _MappingEngine()
    candidates = await _get_candidate_doctypes(inp.session_id)
    user_note = session_context.get("user_import_note", "")
    assignments: List[Dict[str, Any]] = []

    for filename, content in (manifest.get("files") or {}).items():
        if not content:
            continue
        is_unstructured = filename.lower().endswith(".txt") or filename.lower().endswith(".pdf")
        if is_unstructured:
            cls = await classify_doctype(
                filename=filename,
                content_snippet=(content or "")[:2000],
                columns=None,
                candidates=candidates,
                user_import_note=user_note,
                model_name=os.getenv("MAPPING_CLASSIFIER_MODEL"),
            )
            assignments.append({
                "file": filename,
                "doctypes": [cls.get("doctype")] if cls.get("doctype") else [],
                "classification": cls,
            })
            continue

        rows = list(csv.DictReader(io.StringIO(content)))
        clean_rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
        columns = [c for c in list(clean_rows[0].keys()) if c is not None] if clean_rows else []
        split_groups = engine._split_by_entity_type(clean_rows, columns) if clean_rows else None

        if split_groups:
            group_assignments: Dict[str, Any] = {}
            group_doctypes: List[str] = []
            for entity_type, group_rows in split_groups.items():
                group_doctype = None
                kb = engine._load_field_mappings()
                for dt_name in kb.get("doctypes", {}).keys():
                    if entity_type.lower() == dt_name.lower():
                        group_doctype = dt_name
                        break
                if not group_doctype:
                    cls = await classify_doctype(
                        filename=filename,
                        content_snippet=str(entity_type),
                        columns=columns,
                        candidates=candidates,
                        user_import_note=user_note,
                        model_name=os.getenv("MAPPING_CLASSIFIER_MODEL"),
                    )
                    group_doctype = cls.get("doctype")
                if group_doctype and group_doctype not in group_doctypes:
                    group_doctypes.append(group_doctype)
                group_assignments[entity_type] = {
                    "doctype": group_doctype,
                    "rows": len(group_rows),
                }
            assignments.append({
                "file": filename,
                "doctypes": group_doctypes,
                "split": group_assignments,
            })
            continue

        cls = await classify_doctype(
            filename=filename,
            content_snippet="",
            columns=columns,
            candidates=candidates,
            user_import_note=user_note,
            model_name=os.getenv("MAPPING_CLASSIFIER_MODEL"),
        )
        assignments.append({
            "file": filename,
            "doctypes": [cls.get("doctype")] if cls.get("doctype") else [],
            "classification": cls,
        })

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row:
                batches = list(row.file_batches or [])
                if batches:
                    batches[-1]["corpus_assignments"] = assignments
                await db.execute(
                    update(ISSession)
                    .where(ISSession.id == row.id)
                    .values(file_batches=batches, updated_at=datetime.utcnow())
                )
                await db.commit()
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not persist corpus assignments: %s", e)

    activity.logger.info("✅ assign_corpus_doctypes done | files=%d", len(assignments))
    return NodeStatusEnvelope.success(primary_result={"assignments": assignments})


# ── Activity definitions ─────────────────────────────────────────────────────
@activity.defn(name="map_file_to_erpnext")
async def map_file_to_erpnext(inp: MapFileInput) -> Any:
    activity.logger.info("▶ map_file_to_erpnext started | file=%s key=%s hint=%s",
                         inp.filename, inp.r2_manifest_url, inp.doctype_hint)

    s3 = _get_s3_client()
    session_context = await _load_session_context(inp.session_id)
    user_note = session_context.get("user_import_note", "")
    assignment_doctypes = list((inp.corpus_assignment or {}).get("doctypes") or [])
    assignment_split = (inp.corpus_assignment or {}).get("split") or {}

    try:
        response = s3.get_object(Bucket="clean-data", Key=inp.r2_manifest_url)
        raw = response["Body"].read()
        manifest = json.loads(raw.decode("utf-8"))
        content = manifest.get("files", {}).get(inp.filename)
        if not content:
            activity.logger.warning("  ⚠️ File %s not found in manifest", inp.filename)
            return NodeStatusEnvelope.failed(
                errors=[{"code": "FILE_NOT_IN_MANIFEST", "message": f"File '{inp.filename}' not found in manifest"}],
                primary_result={"file": inp.filename},
            )
    except Exception as e:
        activity.logger.error("❌ Failed to download manifest from R2: %s", e)
        return NodeStatusEnvelope.failed(
            errors=[{"code": "MANIFEST_DOWNLOAD_FAILED", "message": "Failed to download manifest from R2", "details": {"error": str(e)}}],
            primary_result={"file": inp.filename},
        )

    engine = _MappingEngine()
    candidates = await _get_candidate_doctypes(inp.session_id)

    # ── New pipeline: Step A (classification) → Step B (extraction/normalization) ──
    # For structured files, extraction is deterministic mapping + folding.
    # For unstructured text, extraction is schema-locked structured output.
    is_unstructured = inp.filename.lower().endswith(".txt") or inp.filename.lower().endswith(".pdf")

    results: List[Dict[str, Any]] = []
    if is_unstructured:
        snippet = (content or "")[:2000]
        hinted_doctype = inp.doctype_hint or (assignment_doctypes[0] if assignment_doctypes else None)
        if hinted_doctype and hinted_doctype in candidates:
            doctype = hinted_doctype
            cls_meta = {"method": "hint", "confidence": 1.0, "signals": ["doctype_hint"]}
        else:
            cls = await classify_doctype(
                filename=inp.filename,
                content_snippet=snippet,
                columns=None,
                candidates=candidates,
                user_import_note=user_note,
                model_name=os.getenv("MAPPING_CLASSIFIER_MODEL"),
            )
            doctype = cls.get("doctype")
            cls_meta = cls

        if doctype == "Unmapped_Irrelevant":
            activity.logger.info("  ⏭️ File %s classified as Unmapped_Irrelevant, skipping extraction.", inp.filename)
            return NodeStatusEnvelope.success(
                primary_result={"file": inp.filename, "doctypes_mapped": [], "status": "unmapped_irrelevant"}
            )

        if not await _should_map_doctype(inp.session_id, doctype, filename=inp.filename):
            activity.logger.info("  ⏭️ Skipping unstructured mapping for %s → %s (not scheduled as 'create' in plan)", inp.filename, doctype)
            return NodeStatusEnvelope.success(
                primary_result={"file": inp.filename, "doctypes_mapped": [], "status": "skipped_by_plan"}
            )

        # Step B: schema-locked extraction
        records: List[Dict[str, Any]] = []
        try:
            records = await extract_unstructured_records(
                doctype=doctype,
                content=content or "",
                filename=inp.filename,
                model_name=os.getenv("MAPPING_EXTRACTION_MODEL"),
                project_id=inp.project_id,
            )
        except Exception as e:
            activity.logger.warning("  ⚠️ Unstructured extraction failed for %s → %s: %s", inp.filename, doctype, e)
            records = []

        records = apply_defaults_and_normalize(
            doctype,
            records,
            context=_defaults_context(session_context, company_slug=inp.company_slug),
        )
        try:
            records = await validate_records_against_schema(doctype, records, project_id=inp.project_id)
        except Exception as e:
            # Keep best-effort normalized records; validation engine will surface issues.
            activity.logger.info("  ⚠️ Schema validation still failing for %s → %s: %s", inp.filename, doctype, str(e)[:160])

        results = [{
            "doctype": doctype,
            "field_mapping": {},   # no column mapping for unstructured
            "rows": records,
            "inferred_doctype": doctype,
            "source_columns": [],
            "_classification": cls_meta,
        }]
    else:
        # Structured CSV/TSV style: deterministic mapping
        rows = list(csv.DictReader(io.StringIO(content)))
        clean_rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
        if not clean_rows:
            clean_rows = []

        columns = [c for c in list(clean_rows[0].keys()) if c is not None] if clean_rows else []

        # Multi-entity split (preserve existing behavior)
        split_groups = engine._split_by_entity_type(clean_rows, columns) if clean_rows else None
        if split_groups:
            for entity_type, group_rows in split_groups.items():
                # Prefer exact doctype name match for entity types
                group_doctype = None
                kb = engine._load_field_mappings()
                for dt_name in kb.get("doctypes", {}).keys():
                    if entity_type.lower() == dt_name.lower() and dt_name in candidates:
                        group_doctype = dt_name
                        break
                if not group_doctype:
                    cls = await classify_doctype(
                        filename=inp.filename,
                        content_snippet=str(entity_type),
                        columns=columns,
                        candidates=candidates,
                    user_import_note=user_note,
                        model_name=os.getenv("MAPPING_CLASSIFIER_MODEL"),
                    )
                    group_doctype = cls.get("doctype")
                if not group_doctype:
                    for split_key, split_val in assignment_split.items():
                        if str(split_key).strip().lower() == str(entity_type).strip().lower():
                            group_doctype = (split_val or {}).get("doctype")
                            break

                group_doctype = resolve_doctype(group_doctype or "")

                if group_doctype == "Unmapped_Irrelevant":
                    activity.logger.info("  ⏭️ Group %s classified as Unmapped_Irrelevant, skipping.", entity_type)
                    continue

                if not await _should_map_doctype(
                    inp.session_id,
                    group_doctype,
                    from_party_split=True,
                    filename=inp.filename,
                ):
                    activity.logger.info("  ⏭️ Skipping split group %s → %s (not scheduled as 'create' in plan)", entity_type, group_doctype)
                    continue

                field_mapping = engine.map_columns(columns, group_doctype, sample_row=group_rows[0] if group_rows else None)
                results.append({
                    "doctype": group_doctype,
                    "field_mapping": field_mapping,
                    "rows": group_rows,
                    "inferred_doctype": group_doctype,
                    "source_columns": columns,
                })
        else:
            # Single doctype
            if inp.doctype_hint and inp.doctype_hint in candidates:
                doctype = inp.doctype_hint
            else:
                implied_dt = filename_implied_doctype(inp.filename)
                if implied_dt and implied_dt in candidates:
                    doctype = implied_dt
                    activity.logger.info(
                        "  📎 Filename prior: %s → %s",
                        inp.filename,
                        doctype,
                    )
                else:
                    cls = await classify_doctype(
                        filename=inp.filename,
                        content_snippet="",
                        columns=columns,
                        candidates=candidates,
                        user_import_note=user_note,
                        model_name=os.getenv("MAPPING_CLASSIFIER_MODEL"),
                    )
                    doctype = cls.get("doctype")
                    if not doctype and assignment_doctypes:
                        doctype = assignment_doctypes[0]

            if doctype == "Unmapped_Irrelevant":
                activity.logger.info("  ⏭️ File %s classified as Unmapped_Irrelevant, skipping mapping.", inp.filename)
                return NodeStatusEnvelope.success(
                    primary_result={"file": inp.filename, "doctypes_mapped": [], "status": "unmapped_irrelevant"}
                )

            implied_dt = filename_implied_doctype(inp.filename)
            if implied_dt and filename_conflicts_with_doctype(inp.filename, doctype or ""):
                if implied_dt in candidates:
                    activity.logger.warning(
                        "  🛡️ Cross-file guard (pre-gate): %s implies %s not %s — remapping",
                        inp.filename,
                        implied_dt,
                        doctype,
                    )
                    doctype = implied_dt
                    if clean_rows:
                        engine.map_columns(columns, doctype, sample_row=clean_rows[0])

            doctype = resolve_doctype(doctype or "")

            if not await _should_map_doctype(inp.session_id, doctype, filename=inp.filename):
                activity.logger.info("  ⏭️ Skipping structured mapping for %s → %s (not scheduled as 'create' in plan)", inp.filename, doctype)
                return NodeStatusEnvelope.success(
                    primary_result={"file": inp.filename, "doctypes_mapped": [], "status": "skipped_by_plan"}
                )

            field_mapping = engine.map_columns(columns, doctype, sample_row=clean_rows[0] if clean_rows else None)
            results = [{
                "doctype": doctype,
                "field_mapping": field_mapping,
                "rows": clean_rows,
                "inferred_doctype": doctype,
                "source_columns": columns,
            }]

    # ── NLP DEDUP: check which doctypes are already mapped by structured files ──
    already_mapped_doctypes: set = set()

    if is_unstructured:
        try:
            async with AsyncSessionLocal() as session:
                # Only treat a doctype as "already mapped" if a structured file actually
                # extracted rows (total_rows > 0). A 0-row mapping (e.g. from a failed
                # unstructured extraction) must NOT block subsequent .txt files from
                # re-attempting the same doctype.
                stmt = select(ISMappedData.target_doctype).where(
                    ISMappedData.session_id == uuid.UUID(inp.session_id),
                    ISMappedData.total_rows > 0,
                )
                res = await session.execute(stmt)
                already_mapped_doctypes = {r[0] for r in res}
        except Exception as e:
            activity.logger.warning("  ⚠️ Could not check existing mappings for dedup: %s", e)

    mapped_doctypes = []
    for result in results:
        doctype = result.get("doctype")
        if not doctype:
            activity.logger.info("  ⚠️ No doctype matched for %s (sub-result)", inp.filename)
            continue

        # Skip NLP-mapped doctypes if a structured file already mapped them 
        if is_unstructured and doctype in already_mapped_doctypes:
            activity.logger.info("  ⏭️ Skipping NLP mapping for %s → %s (already mapped by structured file)",
                                 inp.filename, doctype)
            continue

        rows = result.get("rows", [])
        field_mapping = result.get("field_mapping", {})
        source_columns = result.get("source_columns", [])

        # Cross-file guard: filename strongly implies a different doctype (e.g. active_projects → Project).
        implied_dt = filename_implied_doctype(inp.filename)
        if implied_dt and filename_conflicts_with_doctype(inp.filename, doctype):
            if implied_dt in candidates:
                activity.logger.warning(
                    "  🛡️ Cross-file guard: %s implies %s not %s — remapping",
                    inp.filename,
                    implied_dt,
                    doctype,
                )
                doctype = implied_dt
                if rows and field_mapping and not is_unstructured:
                    cols = source_columns or [c for c in rows[0].keys() if c]
                    field_mapping = engine.map_columns(
                        cols, doctype, sample_row=rows[0] if rows else None
                    )
            else:
                activity.logger.warning(
                    "  ⏭️ Cross-file guard: %s incompatible with %s (implies %s) — skipping",
                    inp.filename,
                    doctype,
                    implied_dt,
                )
                continue

        activity.logger.info("  Mapped %s → %s | fields=%d rows=%d",
                             inp.filename, doctype, len(field_mapping), len(rows))

        slug = inp.company_slug or "unknown"
        rows_key = f"{slug}/{inp.project_id}/mappings/extracted_rows/{doctype}.json"
        payload_key = f"{slug}/{inp.project_id}/mappings/mapped_payloads/{doctype}.json"

        existing_rows = load_r2_json(s3, "clean-data", rows_key)
        if isinstance(existing_rows, list) and existing_rows:
            rows = merge_extracted_rows(doctype, existing_rows, rows)
            activity.logger.info(
                "  🔀 Merged extracted rows for %s → %d total (after dedupe)",
                doctype,
                len(rows),
            )

        try:
            s3.put_object(
                Bucket="clean-data",
                Key=rows_key,
                Body=json.dumps(rows, indent=2, default=str).encode("utf-8"),
                ContentType="application/json",
            )
            activity.logger.info("  ✅ R2 uploaded: clean-data/%s", rows_key)
        except Exception as e:
            activity.logger.error("  ❌ R2 rows upload failed: %s", e)

        mapped_records: List[Dict[str, Any]] = []
        if rows and field_mapping:
            for row in rows:
                mapped_row = {}
                for src_col, val in row.items():
                    if src_col in field_mapping:
                        mapped_row[field_mapping[src_col]] = val
                mapped_records.append(mapped_row)
        elif isinstance(rows, list) and rows and isinstance(rows[0], dict) and not field_mapping:
            # Unstructured pipeline already produced mapped rows (schema-shaped)
            mapped_records = [dict(r) for r in rows]

        # Deterministic folding + defaults + normalization
        mapped_records = fold_child_tables(doctype, mapped_records)
        mapped_records = apply_defaults_and_normalize(
            doctype,
            mapped_records,
            context=_defaults_context(session_context, company_slug=inp.company_slug),
        )
        try:
            mapped_records = await validate_records_against_schema(doctype, mapped_records, project_id=inp.project_id)
        except Exception:
            pass

        mapped_records, quarantined_rows = filter_quarantined_records(doctype, mapped_records)
        if quarantined_rows:
            activity.logger.warning(
                "  🚫 Quarantined %d row(s) for %s (missing identity or cross-entity leak)",
                len(quarantined_rows),
                doctype,
            )

        if not mapped_records:
            activity.logger.info("  ⚠️ No valid rows left for %s after quarantine", doctype)
            continue

        # ── Build link_fields metadata from schema ────────────────────────────
        # Extract every Link field for this doctype from field_mappings.json so
        # the import agent knows which field values need pre-flight seeding.
        # Format: { "fieldname": "TargetDoctype", ... }
        _link_fields: Dict[str, str] = {}
        try:
            from containers.knowledge_base.erpnext.schema.compose import doctype_mapping

            _dt_fields = doctype_mapping(doctype).get("field_mappings", {})
            for _fn, _fc in _dt_fields.items():
                if _fc.get("fieldtype") == "Link":
                    _target = _fc.get("options")
                    _fname = _fc.get("fieldname", _fn)
                    if _target and isinstance(_target, str) and _fname:
                        _link_fields[_fname] = _target
        except Exception as _e:
            activity.logger.warning("  ⚠️ Could not build link_fields metadata for %s: %s", doctype, _e)

        erpnext_payload = {
            "doctype": doctype,
            "link_fields": _link_fields,   # consumed by import agent Pass 2
            "records": mapped_records,
        }

        existing_payload = load_r2_json(s3, "clean-data", payload_key)
        if (
            isinstance(existing_payload, dict)
            and existing_payload.get("records") is not None
            and not filename_conflicts_with_doctype(inp.filename, doctype)
        ):
            prev_count = len(existing_payload.get("records") or [])
            erpnext_payload = merge_payloads(doctype, existing_payload, erpnext_payload)
            activity.logger.info(
                "  🔀 Merged mapped payload for %s: %d + %d → %d records (deduped)",
                doctype,
                prev_count,
                len(mapped_records),
                len(erpnext_payload.get("records") or []),
            )

        
        try:
            s3.put_object(
                Bucket="clean-data",
                Key=payload_key,
                Body=json.dumps(erpnext_payload, indent=2, default=str).encode("utf-8"),
                ContentType="application/json",
            )
            activity.logger.info("  ✅ Mapped payload uploaded to R2.")
        except Exception as e:
            activity.logger.error("  ❌ Failed to upload mapped payload: %s", e)
            
        try:
            async with AsyncSessionLocal() as session:
                for src_col, tgt_field in field_mapping.items():
                    session.add(ISFieldMapping(
                        id=uuid.uuid4(),
                        session_id=uuid.UUID(inp.session_id),
                        source_filename=inp.filename,
                        source_column=src_col,
                        target_doctype=doctype,
                        target_field=tgt_field,
                        mapping_method="exact_match",
                    ))

                session.add(ISMappedData(
                    id=uuid.uuid4(),
                    session_id=uuid.UUID(inp.session_id),
                    target_doctype=doctype,
                    source_filename=inp.filename,
                    extracted_rows_r2_path=rows_key,
                    mapped_payload_r2_path=payload_key,
                    total_rows=len(rows),
                    total_mapped_fields=len(field_mapping),
                    validation_status="pending",
                ))
                await session.commit()
                activity.logger.info("  ✅ is_field_mappings (%d rows) + is_mapped_data upserted for %s",
                                     len(field_mapping), doctype)

        except Exception as e:
            activity.logger.error("  ❌ Supabase write failed: %s", e)

        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="mapping_completed",
            actor="system",
            entity_type="mapping",
            details={"doctype": doctype, "source_file": inp.filename, "fields_mapped": len(field_mapping), "rows": len(rows)},
            result="success",
        )
        mapped_doctypes.append(doctype)

    if not mapped_doctypes:
        activity.logger.info("  ⚠️ No doctypes mapped for %s", inp.filename)
        return NodeStatusEnvelope.partial(
            primary_result={"file": inp.filename, "doctypes_mapped": []},
            warnings=[{"code": "NO_DOCTYPES_MAPPED", "message": f"No doctypes mapped for file '{inp.filename}'"}],
        )

    activity.logger.info("✅ map_file_to_erpnext done | doctypes=%s", mapped_doctypes)
    return NodeStatusEnvelope.success(primary_result={"file": inp.filename, "doctypes_mapped": mapped_doctypes})


@activity.defn(name="infer_doctype_from_columns")
async def infer_doctype_from_columns(inp: MapColumnsInput) -> Dict[str, Any]:
    activity.logger.info("▶ infer_doctype_from_columns started | columns=%s", inp.columns[:5])
    engine = _MappingEngine()
    doctype = engine.infer_doctype(inp.columns)
    field_mapping = engine.map_columns(inp.columns, doctype or inp.doctype_hint)
    activity.logger.info("✅ infer_doctype_from_columns done | doctype=%s", doctype)
    return {"doctype": doctype, "field_mapping": field_mapping}


# ── STEP 10: CONVERSATIONAL REFINEMENT ───────────────────────────────────────

@activity.defn(name="refine_mapping_with_llm")
async def refine_mapping_with_llm(inp: RefineMappingInput) -> Dict[str, Any]:
    activity.logger.info("▶ refine_mapping_with_llm started | session=%s feedback='%s'", inp.session_id, inp.user_feedback)
    
    current_mappings = []
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(ISFieldMapping).where(ISFieldMapping.session_id == uuid.UUID(inp.session_id))
            res = await session.execute(stmt)
            records = res.scalars().all()
            for r in records:
                current_mappings.append({
                    "mapping_id": str(r.id),
                    "source_column": r.source_column,
                    "target_doctype": r.target_doctype,
                    "target_field": r.target_field
                })
    except Exception as e:
        activity.logger.error("  ❌ Failed to fetch current mappings: %s", e)
        return {"error": "DB read failed"}

    if not current_mappings:
        return {"status": "no_mappings_found"}

    prompt = REFINE_MAPPING_PROMPT.format(
        current_mappings=json.dumps(current_mappings, indent=2),
        user_feedback=inp.user_feedback
    )

    try:
        llm_response = generate_json(prompt, temperature=0.1, max_output_tokens=1500)
    except Exception as e:
        activity.logger.error("  ❌ LLM refinement failed: %s", e)
        return {"error": "LLM failed"}

    updated_mappings = llm_response.get("updated_mappings", [])
    removed_mappings = llm_response.get("removed_mappings", [])
    affected_doctypes = set()

    try:
        async with AsyncSessionLocal() as session:
            for update_item in updated_mappings:
                map_id = update_item.get("mapping_id")
                new_field = update_item.get("new_target_field")
                reasoning = update_item.get("reasoning")
                
                await session.execute(
                    update(ISFieldMapping)
                    .where(ISFieldMapping.id == uuid.UUID(map_id))
                    .values(
                        target_field=new_field,
                        user_corrected=True,
                        user_correction=json.dumps({"feedback": inp.user_feedback, "new_field": new_field, "reasoning": reasoning})
                    )
                )
                
                # Fetch to get doctype for R2 regen
                res = await session.execute(select(ISFieldMapping.target_doctype, ISFieldMapping.source_column).where(ISFieldMapping.id == uuid.UUID(map_id)))
                row = res.first()
                if row:
                    affected_doctypes.add(row[0])
                    # 🚀 UNCOMMENT THIS BLOCK: Log to History Table
                    session.add(ISFieldMappingHistory(
                        session_id=uuid.UUID(inp.session_id),
                        source_column=row[1],
                        target_doctype=row[0],
                        target_field=new_field,
                        user_confirmed=True,
                        user_corrected=True
                    ))

            for remove_item in removed_mappings:
                map_id = remove_item.get("mapping_id")
                res = await session.execute(select(ISFieldMapping.target_doctype).where(ISFieldMapping.id == uuid.UUID(map_id)))
                row = res.first()
                if row:
                    affected_doctypes.add(row[0])

                await session.execute(
                    delete(ISFieldMapping).where(ISFieldMapping.id == uuid.UUID(map_id))
                )
            
            await session.commit()
    except Exception as e:
        activity.logger.error("  ❌ DB update failed: %s", e)

    s3 = _get_s3_client()
    for doctype in affected_doctypes:
        try:
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(ISFieldMapping).where(
                    ISFieldMapping.session_id == uuid.UUID(inp.session_id),
                    ISFieldMapping.target_doctype == doctype
                ))
                active_mappings = {r.source_column: r.target_field for r in res.scalars().all()}
                
                res_meta = await session.execute(select(ISMappedData).where(
                    ISMappedData.session_id == uuid.UUID(inp.session_id),
                    ISMappedData.target_doctype == doctype
                ))
                meta = res_meta.scalars().first()

            if not meta or not meta.extracted_rows_r2_path:
                continue
            
            response = s3.get_object(Bucket="clean-data", Key=meta.extracted_rows_r2_path)
            raw_rows = json.loads(response["Body"].read().decode("utf-8"))
            
            new_mapped_records = []
            for row in raw_rows:
                mapped_row = {}
                for src_col, val in row.items():
                    if src_col in active_mappings:
                        mapped_row[active_mappings[src_col]] = val
                new_mapped_records.append(mapped_row)
                
            erpnext_payload = {"doctype": doctype, "records": new_mapped_records}
            
            s3.put_object(
                Bucket="clean-data",
                Key=meta.mapped_payload_r2_path,
                Body=json.dumps(erpnext_payload, indent=2, default=str).encode("utf-8"),
                ContentType="application/json",
            )
            activity.logger.info("  ✅ Regenerated payload for %s", doctype)
            
        except Exception as e:
            activity.logger.error("  ❌ Failed to regenerate payload for %s: %s", doctype, e)

    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="mapping_refined",
        actor="user",
        details={"changes": len(updated_mappings) + len(removed_mappings), "feedback": inp.user_feedback},
        result="success",
    )

    activity.logger.info("✅ refine_mapping_with_llm done | changes=%d", len(updated_mappings) + len(removed_mappings))
    
    return {
        "updated_mappings": updated_mappings,
        "removed_mappings": removed_mappings,
        "changes_count": len(updated_mappings) + len(removed_mappings)
    }