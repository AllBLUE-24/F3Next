"""
File IO — fetch_clean_files activity.

Reads actual file content from the R2 'clean-data' bucket, writes a
consolidated manifest JSON back to R2, and returns the R2 key as a string.

Temporal event history only sees a tiny string — never raw file content.

Only reads text-parseable formats: .csv, .json, .xml, .sql, .txt, .tsv
Skips binary blobs (.xlsx, .zip, .gz, .pdf, .png, etc.)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity


# Formats we can safely decode as UTF-8 text or parse structurally
TEXT_EXTENSIONS = {".csv", ".json", ".xml", ".sql", ".txt", ".tsv", ".xlsx"}

# Max file size we'll read into memory (10 MB)
MAX_FILE_BYTES = 10 * 1024 * 1024


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _is_text_file(filename: str) -> bool:
    """Check if file extension is in our text-parseable set."""
    dot = filename.rfind(".")
    if dot == -1:
        return False
    ext = filename[dot:].lower()
    return ext in TEXT_EXTENSIONS


@dataclass
class FetchCleanFilesInput:
    """Input for the fetch_clean_files activity."""
    uploaded_files: List[Dict[str, Any]]
    project_id: str = ""
    company_slug: str = "unknown"


@activity.defn(name="fetch_clean_files")
async def fetch_clean_files(inp: FetchCleanFilesInput) -> Dict[str, Any]:
    """
    Read text-parseable files from R2 clean-data bucket, write a consolidated
    manifest to R2, and return the R2 key.

    Manifest JSON structure: {files: {filename: content_str, ...}, file_count: N, _created_at: ...}

    Returns: {"manifest_url": str, "parsed_files": List[str]}
    """
    activity.logger.info("▶ fetch_clean_files started | %d files to check", len(inp.uploaded_files))

    s3 = _get_s3_client()
    contents: Dict[str, str] = {}

    for file_info in inp.uploaded_files:
        fname = file_info.get("file_name", "")
        obj_key = file_info.get("object_path", "")

        if not obj_key:
            activity.logger.warning("  ⚠️ Skipping entry with no object_path: %s", file_info)
            continue

        if not _is_text_file(fname):
            activity.logger.info("  ⏭️  Skipping binary file: %s", fname)
            continue

        try:
            # Check size first via HEAD
            head = s3.head_object(Bucket="clean-data", Key=obj_key)
            size = head.get("ContentLength", 0)

            if size > MAX_FILE_BYTES:
                activity.logger.warning("  ⚠️ File too large (%d bytes), skipping: %s", size, fname)
                continue

            # Read content
            response = s3.get_object(Bucket="clean-data", Key=obj_key)
            raw_bytes = response["Body"].read()

            # Decode or parse based on extension
            if fname.lower().endswith(".xlsx"):
                import pandas as pd
                import io
                try:
                    df_dict = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=None)
                    for sheet_name, df in df_dict.items():
                        # Drop completely empty rows/columns to keep CSV clean
                        df = df.dropna(how='all').dropna(axis=1, how='all')
                        if not df.empty:
                            csv_str = df.to_csv(index=False)
                            virtual_fname = f"{fname} - {sheet_name}.csv"
                            contents[virtual_fname] = csv_str
                    activity.logger.info("  ✅ Parsed Excel %s (%d sheets)", fname, len(df_dict))
                except Exception as ex:
                    activity.logger.error("  ❌ Failed to parse Excel %s: %s", fname, ex)
            else:
                try:
                    text = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw_bytes.decode("latin-1")

                contents[fname] = text
                activity.logger.info("  ✅ Read %s (%d bytes, %d lines)",
                                     fname, len(raw_bytes), text.count("\n") + 1)

        except Exception as e:
            activity.logger.error("  ❌ Failed to read %s from clean-data: %s", fname, e)
            continue

    # ── Write consolidated manifest to R2 ────────────────────────────────────
    slug = inp.company_slug or "unknown"
    manifest_key = f"{slug}/{inp.project_id}/_file_contents/manifest.json"

    try:
        manifest = {
            "files": contents,
            "file_count": len(contents),
            "_created_at": datetime.utcnow().isoformat() + "Z",
        }
        s3.put_object(
            Bucket="clean-data",
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ Manifest uploaded to clean-data/%s", manifest_key)
    except Exception as e:
        activity.logger.error("  ❌ Failed to upload manifest: %s", e)
        manifest_key = f"error:{e}"

    activity.logger.info("✅ fetch_clean_files done | read %d/%d files → manifest=%s",
                         len(contents), len(inp.uploaded_files), manifest_key)
    
    # ── Update is_files in Supabase ──────────────────────────────────────────
    try:
        from shared.database.db import AsyncSessionLocal
        from shared.models.is_models import ISFile
        from sqlalchemy import select, update
        import asyncio

        async def _update_db():
            async with AsyncSessionLocal() as session:
                for file_info in inp.uploaded_files:
                    obj_key = file_info.get("object_path")
                    if not obj_key:
                        continue
                    
                    # Update the row where the r2_object_key matches
                    stmt = select(ISFile).where(ISFile.r2_object_key == obj_key)
                    result = await session.execute(stmt)
                    file_row = result.scalar_one_or_none()

                    if file_row:
                        await session.execute(
                            update(ISFile)
                            .where(ISFile.id == file_row.id)
                            .values(
                                parsed=True, 
                                included_in_manifest=True, 
                                parsed_at=datetime.utcnow()
                            )
                        )
                await session.commit()
                
        # Run DB update (if your activity is sync, use asyncio.run. If async, just await)
        # Note: If your fetch_clean_files activity is defined as `async def`, remove `asyncio.run` 
        # and just `await _update_db()`.
        asyncio.run(_update_db()) 
        activity.logger.info("  ✅ is_files updated with parsed status")
    except Exception as e:
        activity.logger.error("  ❌ Failed to update is_files parsed status: %s", e)
    
    return {
        "manifest_url": manifest_key,
        "parsed_files": list(contents.keys())
    }
