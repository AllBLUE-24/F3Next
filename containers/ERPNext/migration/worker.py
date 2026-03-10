# containers/ERPNext/migration/worker.py
import asyncio
import os
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# --- ADD THIS CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

# Import the Workflow and Activities
from .workflows import LegacyDataMigrationWorkflow
from .activities import (
    download_and_extract_schema,
    generate_mapping_proposal,
    transform_and_upload,
    trigger_validation_agent
)

async def main():
    # Connect to Temporal Server
    # In Docker compose, host might be 'temporal' instead of 'localhost'
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

    # Define the worker
    worker = Worker(
        client,
        task_queue="legacy-migration-queue",
        workflows=[LegacyDataMigrationWorkflow],
        activities=[
            download_and_extract_schema,
            generate_mapping_proposal,
            transform_and_upload,
            trigger_validation_agent
        ],
    )

    print("Migration Agent Worker started... waiting for tasks.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())