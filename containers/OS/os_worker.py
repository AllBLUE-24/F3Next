"""
containers/OS/os_worker.py

THE single Temporal worker for the entire ERP-OS pipeline.
All 9 Agents are now LIVE! 🚀
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.contrib.pydantic import pydantic_data_converter

from containers.OS.os_workflow.workflow import ERPOSCommandWorkflow

# ── ALL 9 REAL ACTIVITIES ──────────────────────────────────────────────────────
from containers.OS.clarity_agent.activities import extract_intent, resolve_ambiguity
from containers.OS.context_retrieval.activities import retrieve_context
from containers.OS.command_planner.activities import plan_command
from containers.OS.payload_generator.activities import generate_payload
from containers.OS.validation_agent.activities import validate_payload
from containers.OS.execution_agent.activities import execute_command
from containers.OS.result_formatter.activities import format_result  # ✅ AGENT 9 LIVE

# ── Config ─────────────────────────────────────────────────────────────────────
TASK_QUEUE    = "os-main-queue"
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger("os_worker")


async def run_worker() -> None:
    logger.info("━" * 60)
    logger.info("ERP-OS Worker starting")
    logger.info("Temporal : %s", TEMPORAL_HOST)
    logger.info("Queue    : %s", TASK_QUEUE)
    logger.info("━" * 60)

    client = await Client.connect(TEMPORAL_HOST, data_converter=pydantic_data_converter)

    worker = Worker(
        client,
        task_queue = TASK_QUEUE,
        workflows  = [ERPOSCommandWorkflow],
        activities = [
            extract_intent,
            resolve_ambiguity,
            retrieve_context,
            plan_command,
            generate_payload,
            validate_payload,
            execute_command,     
            format_result,     # ✅ REAL Result Formatter
        ],
        max_concurrent_activities     = 20,
        max_concurrent_workflow_tasks = 10,
    )

    logger.info("")
    logger.info("✅ Activities registered:")
    logger.info("   ✅ extract_intent       (Clarity Agent)")
    logger.info("   ✅ resolve_ambiguity    (Clarity Agent)")
    logger.info("   ✅ retrieve_context     (Context Retrieval)")
    logger.info("   ✅ plan_command         (Command Planner)")
    logger.info("   ✅ generate_payload     (Payload Generator)")
    logger.info("   ✅ validate_payload     (Validation Agent)")
    logger.info("   ✅ execute_command      (Execution Agent)")
    logger.info("   ✅ format_result        (Result Formatter)")
    logger.info("")
    logger.info("🟢 FULL PIPELINE LIVE — waiting for commands...")
    logger.info("   Press Ctrl+C to stop.")
    logger.info("")

    if sys.platform != "win32":
        import signal
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(worker)))

    async with worker:
        await asyncio.Event().wait()


async def _shutdown(worker: Worker) -> None:
    logger.info("Shutting down OS worker...")
    await worker.shutdown()
    logger.info("Worker stopped.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("OS worker stopped.")