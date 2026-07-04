"""
shared/r2_client.py

Reusable Cloudflare R2 client (boto3 S3-compatible).

Used by:
  - CVS (Context Versioning Service): context/{company_slug}/{layer}/v{version:05d}.json
  - Implementation System: quarantine/{company_slug}/{project_id}/{filename}

Usage:
    from shared.r2_client import r2_write_json, r2_read_json, r2_key_for_context

    key = r2_key_for_context(company_slug, "master_data", version=42)
    await r2_write_json(key, {"customers": [...]}, bucket="context-store")
    data = await r2_read_json(key, bucket="context-store")

Design rules:
  - All functions are async-friendly (run boto3 in executor to avoid blocking)
  - Never raises — logs and returns None/False on failure
  - Bucket names are passed explicitly (quarantine vs. context-store)
  - Credentials always come from env vars (never hardcoded)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from functools import partial
from typing import Any, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ── R2 bucket names ───────────────────────────────────────────────────────────
R2_BUCKET_CONTEXT    = "context-store"   # CVS snapshots
R2_BUCKET_QUARANTINE = "quarantine"      # IS file uploads


def _make_client():
    """Build a boto3 S3 client pointed at Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url          = os.getenv("R2_ENDPOINT"),
        aws_access_key_id     = os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY"),
        config                = Config(signature_version="s3v4"),
        region_name           = "auto",
    )


# ── Key helpers ───────────────────────────────────────────────────────────────

def r2_key_for_context(company_slug: str, layer: str, version: int) -> str:
    """
    Build the R2 object key for a context snapshot.

    e.g. context/sunrise-foods/master_data/v00042.json
    """
    return f"context/{company_slug}/{layer}/v{version:05d}.json"


def r2_key_latest(company_slug: str, layer: str) -> str:
    """
    Build the R2 object key for the 'latest' pointer file.
    This is a tiny JSON file that points to the latest versioned key.

    e.g. context/sunrise-foods/master_data/latest.json
    """
    return f"context/{company_slug}/{layer}/latest.json"


# ── Core operations (sync, run in executor) ───────────────────────────────────

def _sync_write_json(key: str, data: dict, bucket: str) -> bool:
    """Synchronous R2 write. Run in executor."""
    try:
        client = _make_client()
        body   = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        client.put_object(
            Bucket      = bucket,
            Key         = key,
            Body        = body,
            ContentType = "application/json",
        )
        logger.debug("R2 write OK: bucket=%s key=%s bytes=%d", bucket, key, len(body))
        return True
    except ClientError as e:
        logger.error("R2 write failed: bucket=%s key=%s error=%s", bucket, key, e)
        return False
    except Exception as e:
        logger.exception("R2 write unexpected error: bucket=%s key=%s", bucket, key)
        return False


def _sync_read_json(key: str, bucket: str) -> Optional[dict]:
    """Synchronous R2 read. Run in executor."""
    try:
        client   = _make_client()
        response = client.get_object(Bucket=bucket, Key=key)
        body     = response["Body"].read()
        return json.loads(body)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchKey", "404"):
            logger.debug("R2 key not found: bucket=%s key=%s", bucket, key)
        else:
            logger.error("R2 read failed: bucket=%s key=%s error=%s", bucket, key, e)
        return None
    except Exception as e:
        logger.exception("R2 read unexpected error: bucket=%s key=%s", bucket, key)
        return None


def _sync_delete(key: str, bucket: str) -> bool:
    """Synchronous R2 delete. Run in executor."""
    try:
        client = _make_client()
        client.delete_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        logger.error("R2 delete failed: bucket=%s key=%s error=%s", bucket, key, e)
        return False


# ── Async public API ──────────────────────────────────────────────────────────

async def r2_write_json(
    key:    str,
    data:   dict,
    bucket: str = R2_BUCKET_CONTEXT,
) -> bool:
    """
    Write a dict as JSON to R2.

    Args:
        key:    R2 object key (use r2_key_for_context() helpers)
        data:   Python dict to serialise
        bucket: R2 bucket name (default: context-store)

    Returns:
        True on success, False on any error (never raises).
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_sync_write_json, key, data, bucket))


def _sync_object_size(key: str, bucket: str) -> int:
    """Return R2 object ContentLength, or -1 on error."""
    try:
        client = _make_client()
        resp = client.head_object(Bucket=bucket, Key=key)
        return int(resp.get("ContentLength", 0))
    except Exception:
        return -1


async def r2_object_size(key: str, bucket: str = R2_BUCKET_CONTEXT) -> int:
    """Async wrapper for head_object ContentLength."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_sync_object_size, key, bucket))


async def r2_write_json_verified(
    key: str,
    data: dict,
    *,
    bucket: str = R2_BUCKET_CONTEXT,
    min_bytes: int = 3,
) -> bool:
    """Write JSON to R2 and verify non-empty object landed."""
    if not data:
        logger.error("R2 write refused: empty payload | key=%s", key)
        return False
    ok = await r2_write_json(key, data, bucket=bucket)
    if not ok:
        return False
    size = await r2_object_size(key, bucket=bucket)
    if size < min_bytes:
        logger.error("R2 write verification failed: key=%s size=%d", key, size)
        return False
    return True


async def r2_read_json(
    key:    str,
    bucket: str = R2_BUCKET_CONTEXT,
) -> Optional[dict]:
    """
    Read a JSON object from R2.

    Returns:
        Parsed dict, or None if key doesn't exist or read fails.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_sync_read_json, key, bucket))


async def r2_write_context_snapshot(
    company_slug: str,
    layer:        str,
    version:      int,
    data:         dict,
) -> str:
    """
    Write a versioned context snapshot and update the 'latest' pointer.

    Returns:
        The R2 key written (e.g. "context/sunrise-foods/master_data/v00042.json")
    """
    versioned_key = r2_key_for_context(company_slug, layer, version)
    latest_key    = r2_key_latest(company_slug, layer)

    latest_pointer = {
        "version":     version,
        "key":         versioned_key,
        "company_slug": company_slug,
        "layer":       layer,
    }

    # Write both in parallel
    ok_versioned, ok_latest = await asyncio.gather(
        r2_write_json(versioned_key, data),
        r2_write_json(latest_key, latest_pointer),
    )

    if not ok_versioned:
        logger.error("Failed to write versioned snapshot: %s", versioned_key)
    if not ok_latest:
        logger.warning("Failed to write latest pointer: %s", latest_key)

    return versioned_key


async def r2_read_latest_context(
    company_slug: str,
    layer:        str,
) -> Optional[dict]:
    """
    Read the latest context snapshot for a company + layer from R2.

    First reads the 'latest' pointer to get the current version key,
    then fetches the actual payload.
    """
    latest_key  = r2_key_latest(company_slug, layer)
    pointer     = await r2_read_json(latest_key)

    if not pointer:
        logger.debug("No latest pointer for %s/%s in R2", company_slug, layer)
        return None

    versioned_key = pointer.get("key")
    if not versioned_key:
        return None

    return await r2_read_json(versioned_key)
