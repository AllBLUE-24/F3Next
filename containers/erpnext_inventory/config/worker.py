import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
# REMOVED: from backend.config import TEMPORAL_HOST 

from containers.erpnext_inventory.config.activities import fetch_layer_questions, apply_final_config, save_config_progress, generate_processed_config, save_final_config_db
from containers.erpnext_inventory.config.workflows import ConfigWorkflow

async def main():
    # HARDCODED CONFIGURATION
    TEMPORAL_HOST = "localhost:7233" 

    # Connect to Temporal Server
    client = await Client.connect(TEMPORAL_HOST)
    print(f"✅ Connected to Temporal Server at {TEMPORAL_HOST}")

    # Create Worker
    worker = Worker(
        client,
        task_queue="erpnext-inventory-queue",
        workflows=[ConfigWorkflow],
        activities=[fetch_layer_questions, 
                    generate_processed_config,
                    save_config_progress,
                    save_final_config_db,
                    apply_final_config],
    )

    print("🚀 ERPNext Inventory Config Worker Started...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())