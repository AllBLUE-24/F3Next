"""
containers/context_versioning/cvs_worker.py

Temporal worker entrypoint for the Context Versioning Service.
Registers the CVS workflow and all activities on the cvs-main-queue.

Run via Docker: python -m containers.context_versioning.cvs_worker
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ── Ensure project root is on the path ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from temporalio.client import Client
from temporalio.worker import Worker

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s │ %(name)s │ %(message)s",
    datefmt = "%H:%M:%S",
)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("temporalio.worker").setLevel(logging.ERROR)

# ── Activities ────────────────────────────────────────────────────────────────
from containers.context_versioning.snapshot_builder.activities import build_and_store_snapshot
from containers.context_versioning.context_store.activities import (
    read_latest_snapshot,
    invalidate_session_cache,
    log_context_event,
    register_frappe_webhooks,
    recover_stuck_events,
    cvs_force_sync_for_project,
)

# ── Workflow ───────────────────────────────────────────────────────────────────
from containers.context_versioning.cvs_workflow.workflow import CVSUpdateWorkflow

CVS_QUEUE = "cvs-main-queue"


async def main():
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

    activities_list = [
        build_and_store_snapshot,
        read_latest_snapshot,
        invalidate_session_cache,
        log_context_event,
        register_frappe_webhooks,
        recover_stuck_events,
        cvs_force_sync_for_project,
    ]

    worker = Worker(
        client,
        task_queue = CVS_QUEUE,
        workflows  = [CVSUpdateWorkflow],
        activities = activities_list,
    )

    print("\n┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print("┃              F3NEXT CONTEXT VERSIONING SERVICE              ┃")
    print("┠─────────────────────────────────────────────────────────────┨")
    print("┃  Queue:  cvs-main-queue                                     ┃")
    print("┃  Activities:                                                ┃")
    print("┃    • build_and_store_snapshot (ERPNext → Supabase + R2)     ┃")
    print("┃    • read_latest_snapshot                                   ┃")
    print("┃    • invalidate_session_cache                               ┃")
    print("┃    • log_context_event                                      ┃")
    print("┃    • register_frappe_webhooks  (IS post-deploy)             ┃")
    print("┃    • recover_stuck_events      (recovery cron)              ┃")
    print("┃    • cvs_force_sync_for_project (IS Step 13.5 trigger)      ┃")
    print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    print("🟢 CVS worker live — waiting for sync events...\n")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
