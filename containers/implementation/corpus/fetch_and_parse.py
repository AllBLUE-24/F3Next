"""
Step 2 — fetch_clean_files activity.

Reads file content from R2 clean-data, writes manifest v2 back to R2.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

import boto3
from botocore.config import Config
from temporalio import activity

from containers.implementation.corpus.manifest import build_manifest_v2

TEXT_EXTENSIONS = {".csv", ".json", ".xml", ".sql", ".txt", ".tsv", ".xlsx", ".md"}
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
    dot = filename.rfind(".")
    if dot == -1:
        return False
    ext = filename[dot:].lower()
    return ext in TEXT_EXTENSIONS


@dataclass
class FetchCleanFilesInput:
    uploaded_files: List[Dict[str, Any]]
    project_id: str = ""
    company_slug: str = "unknown"


@activity.defn(name="fetch_clean_files")
async def fetch_clean_files(inp: FetchCleanFilesInput) -> Dict[str, Any]:
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
            head = s3.head_object(Bucket="clean-data", Key=obj_key)
            size = head.get("ContentLength", 0)

            if size > MAX_FILE_BYTES:
                activity.logger.warning("  ⚠️ File too large (%d bytes), skipping: %s", size, fname)
                continue

            response = s3.get_object(Bucket="clean-data", Key=obj_key)
            raw_bytes = response["Body"].read()

            if fname.lower().endswith(".xlsx"):
                import io

                import pandas as pd

                try:
                    df_dict = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=None)
                    for sheet_name, df in df_dict.items():
                        df = df.dropna(how="all").dropna(axis=1, how="all")
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
                activity.logger.info(
                    "  ✅ Read %s (%d bytes, %d lines)",
                    fname, len(raw_bytes), text.count("\n") + 1,
                )

        except Exception as e:
            activity.logger.error("  ❌ Failed to read %s from clean-data: %s", fname, e)
            continue

    slug = inp.company_slug or "unknown"
    manifest_key = f"{slug}/{inp.project_id}/_file_contents/manifest.json"
    created_at = datetime.utcnow().isoformat() + "Z"
    manifest = build_manifest_v2(contents, created_at=created_at)

    try:
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

    activity.logger.info(
        "✅ fetch_clean_files done | read %d/%d files → manifest=%s",
        len(contents), len(inp.uploaded_files), manifest_key,
    )

    meta_summary = {
        fname: {
            "columns": meta.get("columns", []),
            "row_count": meta.get("row_count", 0),
            "is_structured": meta.get("is_structured", False),
        }
        for fname, meta in (manifest.get("file_meta") or {}).items()
    } if manifest_key and not manifest_key.startswith("error") else {}

    return {
        "manifest_url": manifest_key,
        "parsed_files": list(contents.keys()),
        "file_meta_summary": meta_summary,
    }
