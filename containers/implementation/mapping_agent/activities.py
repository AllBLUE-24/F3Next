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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity

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
        if not self._field_mappings and FIELD_MAPPINGS_PATH.exists():
            with open(FIELD_MAPPINGS_PATH, "r", encoding="utf-8") as f:
                self._field_mappings = json.load(f)
        return self._field_mappings

    def infer_doctype(self, columns: List[str], sample_text: Optional[str] = None) -> Optional[str]:
        if columns and len(columns) > 1:
            cols_lower = [c.lower() for c in columns if c is not None]
            data = self._load_field_mappings()
            mappings = data.get("doctypes", {})

            for doctype, config in mappings.items():
                field_mappings = config.get("field_mappings", {})
                match_count = 0
                for field, fconfig in field_mappings.items():
                    synonyms = fconfig.get("user_input_synonyms", [])
                    synonyms.append(fconfig.get("fieldname", field))
                    if any(syn.lower() in c or c in syn.lower() for syn in synonyms for c in cols_lower):
                        match_count += 1
                if match_count >= 2:
                    return doctype

        # Fallback to LLM inference
        from containers.implementation.utils.llm_helper import generate_json
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
        prompt += 'Return JSON: {"doctype": "Exact Doctype Name", "chat_message": "1 short sentence confirming the match"}. If there is absolutely no match, return {"doctype": null, "chat_message": "..."}.'
        
        try:
            res = generate_json(prompt, max_output_tokens=1000)
            return res.get("doctype")
        except Exception as e:
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
        
        # Pass 1: Try synonym match
        for col in columns:
            if col is None:
                continue
            col_lower = col.lower()
            matched = False
            for field, fconfig in field_mappings.items():
                synonyms = fconfig.get("user_input_synonyms", [])
                erp_fieldname = fconfig.get("fieldname", field)
                synonyms.append(erp_fieldname)
                
                if any(syn.lower() in col_lower or col_lower in syn.lower() for syn in synonyms):
                    result[col] = erp_fieldname
                    matched = True
                    break
            if not matched:
                unmapped_cols.append(col)
                
        # Pass 2: Smart LLM Mapping for remaining fields
        if unmapped_cols:
            from containers.implementation.utils.llm_helper import generate_json
            schema = {k: v.get("fieldname", k) for k, v in field_mappings.items()}
            
            prompt = f"Map the following unmapped source columns to the closest matching ERPNext '{doctype}' fields.\n"
            prompt += f"Unmapped source columns: {unmapped_cols}\n"
            prompt += f"Target ERPNext schema fields: {list(schema.values())}\n"
            if sample_row:
                prompt += f"Here is a sample row showing values for context: {sample_row}\n"
            
            prompt += 'Return JSON: { "col1": "erpnext_field1", "col2": "erpnext_field2", "chat_message": "1 short sentence about how many fields were mapped automatically." }. '
            prompt += 'Only map a column if you are highly confident it matches semantics. Otherwise, omit it.'
            
            try:
                llm_map = generate_json(prompt, max_output_tokens=2000)
                for col_name, erp_field in llm_map.items():
                    if col_name in unmapped_cols and erp_field in schema.values():
                        result[col_name] = erp_field
            except Exception as e:
                pass
                
        return result

    def _extract_nlp_rows(self, content: str, doctype: str) -> List[Dict]:
        """Extract structured rows from unstructured text using an LLM."""
        data = self._load_field_mappings()
        field_mappings = data.get("doctypes", {}).get(doctype, {}).get("field_mappings", {})
        schema = {k: v.get("fieldname", k) for k, v in field_mappings.items()}
        
        from containers.implementation.utils.llm_helper import generate_json
        prompt = f"I have unstructured text that represents records for an ERPNext '{doctype}'.\n"
        prompt += f"Extract the data into a structured array of JSON objects.\n"
        prompt += f"Each object should ONLY contain keys from this exact schema: {list(schema.values())}\n"
        prompt += f"Do not invent fields. Use natural inferences for data aggregation if required.\n"
        prompt += f"Here is the text to parse:\n\n{content[:4000]}\n\n"
        prompt += 'Return JSON: { "rows": [ {"field1": "val", "field2": "val"} ] }'
        
        try:
            res = generate_json(prompt, max_output_tokens=4000)
            return res.get("rows", [])
        except Exception:
            return []

    def map_file(self, content: str, filename: str, doctype_hint: Optional[str] = None) -> Dict[str, Any]:
        is_unstructured = filename.lower().endswith(".txt") or filename.lower().endswith(".pdf")
        
        if is_unstructured:
            doctype = doctype_hint or self.infer_doctype([], sample_text=content)
            if not doctype:
                return {"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None, "source_columns": []}
            rows = self._extract_nlp_rows(content, doctype)
            if not rows:
                return {"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None, "source_columns": []}
                
            columns = list(rows[0].keys())
            return {
                "doctype": doctype,
                "field_mapping": {c: c for c in columns}, # Pre-mapped by the LLM
                "rows": rows,
                "inferred_doctype": doctype,
                "source_columns": columns,
            }
        else:
            rows = list(csv.DictReader(io.StringIO(content)))
            clean_rows = [{k: v for k, v in r.items() if k is not None} for r in rows]
            if not clean_rows:
                return {"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None, "source_columns": []}
                
            columns = [c for c in list(clean_rows[0].keys()) if c is not None]
            doctype = doctype_hint or self.infer_doctype(columns)
            field_mapping = self.map_columns(columns, doctype, sample_row=clean_rows[0])
            
            return {
                "doctype": doctype,
                "field_mapping": field_mapping,
                "rows": clean_rows,
                "inferred_doctype": doctype,
                "source_columns": columns,
            }


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class MapFileInput:
    """Input for map_file_to_erpnext. Uses R2 URL instead of raw content."""
    r2_manifest_url: str       # R2 object key to the manifest JSON
    filename: str
    project_id: str
    company_slug: str
    session_id: str
    doctype_hint: Optional[str] = None


@dataclass
class MapColumnsInput:
    columns: List[str]
    doctype_hint: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="map_file_to_erpnext")
async def map_file_to_erpnext(inp: MapFileInput) -> str:
    """
    Download file from R2, map columns to ERPNext doctype, upload results
    to R2, and persist metadata to Supabase is_mappings.

    Returns: doctype name if matched, or "unmapped" if no match found.
    """
    activity.logger.info("▶ map_file_to_erpnext started | file=%s key=%s hint=%s",
                         inp.filename, inp.r2_manifest_url, inp.doctype_hint)

    s3 = _get_s3_client()

    # ── 1. Download manifest from R2 and extract file content ────────────────
    try:
        response = s3.get_object(Bucket="clean-data", Key=inp.r2_manifest_url)
        raw = response["Body"].read()
        manifest = json.loads(raw.decode("utf-8"))
        content = manifest.get("files", {}).get(inp.filename)
        if not content:
            activity.logger.warning("  ⚠️ File %s not found in manifest", inp.filename)
            return "error"
    except Exception as e:
        activity.logger.error("❌ Failed to download manifest from R2: %s", e)
        return "error"

    # ── 2. Run mapping engine ────────────────────────────────────────────────
    engine = _MappingEngine()
    result = engine.map_file(content, inp.filename, inp.doctype_hint)

    doctype = result.get("doctype")
    if not doctype:
        activity.logger.info("  ⚠️ No doctype matched for %s", inp.filename)
        return "unmapped"

    rows = result.get("rows", [])
    field_mapping = result.get("field_mapping", {})
    source_columns = result.get("source_columns", [])

    activity.logger.info("  Mapped %s → %s | fields=%d rows=%d",
                         inp.filename, doctype, len(field_mapping), len(rows))

    # ── 3. Upload extracted rows to R2 ───────────────────────────────────────
    slug = inp.company_slug or "unknown"
    rows_key = f"{slug}/{inp.project_id}/mappings/extracted_rows/{doctype}.json"
    payload_key = f"{slug}/{inp.project_id}/mappings/mapped_payloads/{doctype}.json"

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

    # ── 4. Upload mapped payload metadata to R2 ─────────────────────────────
    try:
        payload = {
            "doctype": doctype,
            "field_mapping": field_mapping,
            "source_columns": source_columns,
            "row_count": len(rows),
            "source_file": inp.filename,
            "r2_extracted_rows_key": rows_key,
        }
        s3.put_object(
            Bucket="clean-data",
            Key=payload_key,
            Body=json.dumps(payload, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", payload_key)
    except Exception as e:
        activity.logger.error("  ❌ R2 payload upload failed: %s", e)

    # ── 5. Persist to Supabase is_mappings ───────────────────────────────────
    try:
        import uuid as _uuid
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISMapping
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISMapping)
                .where(ISMapping.session_id == _uuid.UUID(inp.session_id))
                .where(ISMapping.doctype_name == doctype)
            )
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            mapping_meta = {
                "field_mapping": field_mapping,
                "source_columns": source_columns,
                "r2_extracted_rows_key": rows_key,
                "r2_mapped_payload_key": payload_key,
                "row_count": len(rows),
                "source_file": inp.filename,
            }

            if existing:
                await session.execute(
                    update(ISMapping)
                    .where(ISMapping.id == existing.id)
                    .values(field_mapping=mapping_meta, status="draft")
                )
            else:
                session.add(ISMapping(
                    id=_uuid.uuid4(),
                    session_id=_uuid.UUID(inp.session_id),
                    doctype_name=doctype,
                    field_mapping=mapping_meta,
                    status="draft",
                ))
            await session.commit()
            activity.logger.info("  ✅ is_mappings upserted for %s", doctype)

    except Exception as e:
        activity.logger.error("  ❌ Supabase is_mappings write failed: %s", e)

    activity.logger.info("✅ map_file_to_erpnext done | doctype=%s", doctype)
    return doctype


@activity.defn(name="infer_doctype_from_columns")
async def infer_doctype_from_columns(inp: MapColumnsInput) -> Dict[str, Any]:
    """
    Given a list of column names, infer the best-matching ERPNext doctype
    and return the field mapping without requiring the full CSV.
    (This activity returns a small dict — safe for Temporal.)
    """
    activity.logger.info("▶ infer_doctype_from_columns started | columns=%s", inp.columns[:5])
    engine = _MappingEngine()
    doctype = engine.infer_doctype(inp.columns)
    field_mapping = engine.map_columns(inp.columns, doctype or inp.doctype_hint)
    activity.logger.info("✅ infer_doctype_from_columns done | doctype=%s", doctype)
    return {"doctype": doctype, "field_mapping": field_mapping}