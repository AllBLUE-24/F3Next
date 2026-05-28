import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# DEPRECATED: Discovery chat v4 uses sync POST /api/discovery/chat (no Temporal).
# This worker is kept for migration only — backend-only deploy is sufficient for chat.

from temporalio.client import Client
from temporalio.worker import Worker
from containers.discovery.workflows import DiscoveryChatWorkflow
from containers.discovery.activities import (
    analyze_discovery_turn,
    save_discovery_state,
    generate_erp_recommendation,
    save_discovery_metadata,
)

async def main():
    client = await Client.connect(os.getenv("TEMPORAL_HOST"))
    worker = Worker(
        client,
        task_queue="discovery-queue",  # Isolated from health-check
        workflows=[DiscoveryChatWorkflow],
        activities=[
            analyze_discovery_turn,
            save_discovery_state,
            generate_erp_recommendation,
            save_discovery_metadata,
        ],
    )
    print("Discovery Agent Container: Online & Listening...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())