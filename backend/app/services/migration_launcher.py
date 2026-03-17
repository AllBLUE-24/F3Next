from temporalio.client import Client
import os
import uuid

# Define the task queue name (must match your Worker's task queue)
TASK_QUEUE = "legacy-migration-queue"

async def launch_legacy_migration_workflow(company_slug: str, s3_file_key: str) -> str:
    """
    Connects to Temporal and starts the LegacyDataMigrationWorkflow.
    """
    # Connect to Temporal Server
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))

    # Generate a unique workflow ID
    workflow_id = f"migration-{company_slug}-{uuid.uuid4()}"

    # Start the workflow
    handle = await client.start_workflow(
        "LegacyDataMigrationWorkflow",  # Must match the @workflow.defn name in your workflows.py
        args=[s3_file_key, company_slug], # Arguments passed to the workflow's run method
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    return handle.id