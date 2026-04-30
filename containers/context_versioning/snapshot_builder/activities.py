"""
containers/context_versioning/snapshot_builder/activities.py

Temporal activities for the CVS Snapshot Builder.
Registered on: cvs-main-queue

Activity:
  build_and_store_snapshot — fetches data from ERPNext, writes to Supabase + R2

Input:
  {
    "project_id":     str   — UUID of the project
    "company_slug":   str   — used for R2 key paths
    "company_profile": dict — identity layer (contains ERP credentials)
    "layers":         list  — which layers to rebuild: ["master_data", "transaction_intel"]
    "trigger_event":  str   — "force_sync" / "webhook" / "os_command"
    "trigger_doctype": str  — which doctype triggered this (for webhook events)
  }

Output:
  {
    "success":        bool
    "versions":       dict  — {layer: version_number} for each layer rebuilt
    "r2_keys":        dict  — {layer: r2_key} for each layer
  }
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from temporalio import activity

from containers.context_versioning.snapshot_builder.erp_fetcher import (
    fetch_master_data,
    fetch_transaction_intel,
)

logger = logging.getLogger(__name__)


@activity.defn(name="build_and_store_snapshot")
async def build_and_store_snapshot(data: dict) -> dict:
    """
    Build context snapshot layers from ERPNext and persist to Supabase + R2.

    Steps:
      1. Fetch data from ERPNext for each requested layer
      2. Determine the next version number for each layer
      3. Write to Supabase context_snapshots table
      4. Write to R2 (versioned key + latest pointer)
      5. Return version numbers and R2 keys
    """
    project_id      = data.get("project_id", "")
    company_slug    = data.get("company_slug", "")
    profile         = data.get("company_profile", {})
    layers          = data.get("layers", ["master_data"])
    trigger_event   = data.get("trigger_event", "force_sync")
    trigger_doctype = data.get("trigger_doctype")

    activity.heartbeat("Fetching data from ERPNext")

    results: dict[str, dict] = {}   # layer → {data, version, r2_key}

    # ── Step 1: Fetch ERPNext data for each layer ──────────────────────────────
    for layer in layers:
        activity.heartbeat(f"Fetching {layer}")

        try:
            if layer == "master_data":
                layer_data = await fetch_master_data(profile)

            elif layer == "transaction_intel":
                layer_data = await fetch_transaction_intel(profile, days=30)

            else:
                logger.warning("CVS: unknown layer '%s' — skipping", layer)
                continue

            results[layer] = {"data": layer_data}

        except Exception as e:
            logger.exception("CVS: failed to fetch layer=%s: %s", layer, e)
            results[layer] = {"data": {}, "error": str(e)}

    # ── Step 2: Write to Supabase and R2 ──────────────────────────────────────
    activity.heartbeat("Writing snapshots to Supabase + R2")

    from shared.database.db import AsyncSessionLocal
    from shared.models.cvs_models import ContextSnapshot
    from shared.r2_client import r2_write_context_snapshot
    from sqlalchemy import select, func as sqlfunc

    versions: dict[str, int] = {}
    r2_keys:  dict[str, str] = {}

    async with AsyncSessionLocal() as session:
        for layer, result in results.items():
            if "error" in result and not result["data"]:
                logger.warning("CVS: skipping empty/errored layer=%s", layer)
                continue

            # Get current max version for this project+layer
            max_ver_result = await session.execute(
                select(sqlfunc.max(ContextSnapshot.version)).where(
                    ContextSnapshot.project_id == project_id,
                    ContextSnapshot.layer      == layer,
                )
            )
            current_max = max_ver_result.scalar() or 0
            new_version = current_max + 1

            # Write R2 first (non-blocking; Supabase row has r2_key reference)
            r2_key = await r2_write_context_snapshot(
                company_slug = company_slug,
                layer        = layer,
                version      = new_version,
                data         = result["data"],
            )

            # Write Supabase row
            snapshot = ContextSnapshot(
                project_id      = project_id,
                layer           = layer,
                version         = new_version,
                data            = result["data"],
                trigger_event   = trigger_event,
                trigger_doctype = trigger_doctype,
                r2_key          = r2_key,
            )
            session.add(snapshot)

            versions[layer] = new_version
            r2_keys[layer]  = r2_key

            logger.info(
                "CVS: wrote %s layer v%d → Supabase + R2 key=%s",
                layer, new_version, r2_key,
            )

        await session.commit()

    activity.heartbeat("Snapshot complete")

    return {
        "success":  len(versions) > 0,
        "versions": versions,
        "r2_keys":  r2_keys,
        "layers_built": list(versions.keys()),
    }
