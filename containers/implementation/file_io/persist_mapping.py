"""
File IO — persist_mapping activity.

Writes mapped doctype data to R2 and upserts the is_mappings table.
Heavy payloads (extracted rows, mapped payloads) go to R2.
Supabase stores only metadata + R2 URLs.
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
    field_mapping: Dict[str, str]
    extracted_rows: List[Dict[str, Any]]
    source_columns: List[str] = field(default_factory=list)
    inferred_doctype: Optional[str] = None


@activity.defn(name="persist_mapping")
async def persist_mapping(inp: PersistMappingInput) -> str:
    """
    Persist mapping results:
      1. Upload extracted rows → R2 (clean_data/{slug}/{project}/mappings/extracted_rows/{doctype}.json)
      2. Upload mapped payload → R2 (clean_data/{slug}/{project}/mappings/mapped_payloads/{doctype}.json)
      3. Upsert is_mappings row with R2 URLs + field mapping metadata

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
        rows_key = None

    # ── 2. Upload mapped payload to R2 ───────────────────────────────────────
    mapped_payload = {
        "doctype": inp.doctype_name,
        "field_mapping": inp.field_mapping,
        "source_columns": inp.source_columns,
        "inferred_doctype": inp.inferred_doctype,
        "row_count": len(inp.extracted_rows),
        "r2_extracted_rows_key": rows_key,
        "_persisted_at": datetime.utcnow().isoformat() + "Z",
    }
    payload_key = f"{slug}/{inp.project_id}/mappings/mapped_payloads/{inp.doctype_name}.json"
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

    # ── 3. Upsert is_mappings row ────────────────────────────────────────────
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISMapping
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as session:
            # Check for existing mapping for this session + doctype
            stmt = (
                select(ISMapping)
                .where(ISMapping.session_id == uuid.UUID(inp.session_id))
                .where(ISMapping.doctype_name == inp.doctype_name)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            mapping_meta = {
                "field_mapping": inp.field_mapping,
                "source_columns": inp.source_columns,
                "r2_extracted_rows_key": rows_key,
                "r2_mapped_payload_key": payload_key,
                "row_count": len(inp.extracted_rows),
            }

            if existing:
                await session.execute(
                    update(ISMapping)
                    .where(ISMapping.id == existing.id)
                    .values(
                        field_mapping=mapping_meta,
                        status="draft",
                    )
                )
            else:
                new_mapping = ISMapping(
                    id=uuid.uuid4(),
                    session_id=uuid.UUID(inp.session_id),
                    doctype_name=inp.doctype_name,
                    field_mapping=mapping_meta,
                    status="draft",
                )
                session.add(new_mapping)

            await session.commit()
            activity.logger.info("  ✅ Supabase is_mappings upserted for %s", inp.doctype_name)

    except Exception as e:
        activity.logger.error("  ❌ Supabase is_mappings write failed: %s", e)

    activity.logger.info("✅ persist_mapping done | doctype=%s", inp.doctype_name)
    return "success"
