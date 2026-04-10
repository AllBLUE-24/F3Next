"""
File IO — persist_mapping activity.

Writes mapping results to the normalised v2 schema:
  1. is_field_mappings  — one row per column → ERPNext field mapping
  2. is_mapped_data     — one row per doctype with R2 references
  3. R2                 — extracted rows + mapped payloads (unchanged)

Returns: "success" (tiny string for Temporal)
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
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


@dataclass
class PersistMappingInput:
    session_id: str
    project_id: str
    company_slug: str
    doctype_name: str
    field_mapping: Dict[str, str]       # {source_col: erpnext_field, ...}
    extracted_rows: List[Dict[str, Any]]
    source_filename: str = ""
    source_columns: List[str] = field(default_factory=list)
    mapping_methods: Optional[Dict[str, str]] = None  # {source_col: method, ...}
    mapping_confidences: Optional[Dict[str, float]] = None  # {source_col: confidence}
    file_id: Optional[str] = None


@activity.defn(name="persist_mapping")
async def persist_mapping(inp: PersistMappingInput) -> str:
    """
    Persist mapping results:
      1. Upload extracted rows → R2
      2. Upload mapped payload → R2
      3. Insert is_field_mappings rows (one per column mapping)
      4. Insert is_mapped_data row (R2 refs + summary)

    Returns: "success"
    """
    activity.logger.info(
        "▶ persist_mapping started | session=%s doctype=%s rows=%d",
        inp.session_id, inp.doctype_name, len(inp.extracted_rows),
    )

    slug = inp.company_slug or "unknown"
    s3 = _get_s3_client()

    # ── 1. Upload extracted rows to R2 ───────────────────────────────────────
    rows_key = f"{slug}/{inp.project_id}/mappings/extracted_rows/{inp.doctype_name}.json"
    try:
        s3.put_object(
            Bucket="clean-data",
            Key=rows_key,
            Body=json.dumps(inp.extracted_rows, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded extracted rows: clean-data/%s", rows_key)
    except Exception as e:
        activity.logger.error("  ❌ R2 upload failed for extracted rows: %s", e)
        rows_key = ""

    # ── 2. Upload mapped payload to R2 ───────────────────────────────────────
    payload_key = f"{slug}/{inp.project_id}/mappings/mapped_payloads/{inp.doctype_name}.json"
    mapped_payload = {
        "doctype": inp.doctype_name,
        "field_mapping": inp.field_mapping,
        "source_columns": inp.source_columns,
        "row_count": len(inp.extracted_rows),
        "r2_extracted_rows_key": rows_key,
        "_persisted_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        s3.put_object(
            Bucket="clean-data",
            Key=payload_key,
            Body=json.dumps(mapped_payload, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded mapped payload: clean-data/%s", payload_key)
    except Exception as e:
        activity.logger.error("  ❌ R2 upload failed for mapped payload: %s", e)

    # ── 3. Insert is_field_mappings rows ─────────────────────────────────────
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISFieldMapping, ISMappedData

        methods = inp.mapping_methods or {}
        confidences = inp.mapping_confidences or {}

        async with AsyncSessionLocal() as session:
            for src_col, tgt_field in inp.field_mapping.items():
                session.add(ISFieldMapping(
                    id=uuid.uuid4(),
                    session_id=uuid.UUID(inp.session_id),
                    file_id=uuid.UUID(inp.file_id) if inp.file_id else None,
                    source_filename=inp.source_filename,
                    source_column=src_col,
                    target_doctype=inp.doctype_name,
                    target_field=tgt_field,
                    mapping_method=methods.get(src_col, "exact_match"),
                    confidence=confidences.get(src_col),
                ))

            activity.logger.info("  ✅ Inserted %d is_field_mappings rows", len(inp.field_mapping))

            # ── 4. Insert is_mapped_data row ─────────────────────────────────
            session.add(ISMappedData(
                id=uuid.uuid4(),
                session_id=uuid.UUID(inp.session_id),
                file_id=uuid.UUID(inp.file_id) if inp.file_id else None,
                target_doctype=inp.doctype_name,
                source_filename=inp.source_filename,
                extracted_rows_r2_path=rows_key,
                mapped_payload_r2_path=payload_key,
                total_rows=len(inp.extracted_rows),
                total_mapped_fields=len(inp.field_mapping),
                validation_status="pending",
            ))

            await session.commit()
            activity.logger.info("  ✅ Supabase is_mapped_data inserted for %s", inp.doctype_name)

    except Exception as e:
        activity.logger.error("  ❌ Supabase write failed: %s", e)

    # ── 5. Audit trail ───────────────────────────────────────────────────────
    from containers.implementation.file_io.persist_audit import log_audit
    await log_audit(
        session_id=inp.session_id,
        action="mapping_completed",
        actor="system",
        entity_type="mapping",
        details={
            "doctype": inp.doctype_name,
            "source_file": inp.source_filename,
            "fields_mapped": len(inp.field_mapping),
            "rows": len(inp.extracted_rows),
        },
        result="success",
    )

    activity.logger.info("✅ persist_mapping done | doctype=%s", inp.doctype_name)
    return "success"
