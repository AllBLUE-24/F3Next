"""
containers/cascade/cascade_worker.py

Temporal worker for the operations control plane (cascade notifications).
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from temporalio.client import Client
from temporalio.worker import Worker

from containers.cascade.cascade_workflow.workflow import (
    CASCADE_QUEUE,
    CascadeEventWorkflow,
)
from containers.cascade.dispatcher.activities import dispatch_notifications
from containers.cascade.event_intake.activities import (
    log_cascade_event,
    mark_cascade_processed,
)
from containers.cascade.recipient_resolver.activities import resolve_recipients
from containers.cascade.rule_resolver.activities import resolve_cascade_rules
from containers.cascade.translator.activities import translate_event_to_messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("temporalio.worker").setLevel(logging.ERROR)


async def main() -> None:
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

    activities = [
        log_cascade_event,
        mark_cascade_processed,
        resolve_cascade_rules,
        translate_event_to_messages,
        resolve_recipients,
        dispatch_notifications,
    ]

    worker = Worker(
        client,
        task_queue=CASCADE_QUEUE,
        workflows=[CascadeEventWorkflow],
        activities=activities,
    )

    print("\n+----------------------------------------------------------+")
    print("|           F3NEXT CASCADE / CONTROL PLANE WORKER          |")
    print("+----------------------------------------------------------+")
    print(f"|  Queue: {CASCADE_QUEUE:<47}|")
    print("|  Activities: log, rules, translate, recipients, dispatch |")
    print("+----------------------------------------------------------+")
    print("Cascade worker live — waiting for ERPNext events...\n")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
