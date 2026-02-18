import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

# Adjust imports to match your folder structure
from containers.erpnext_inventory.config_apply.workflows import ConfigApplyWorkflow
from containers.erpnext_inventory.config_apply.activities import ConfigApplyActivities

async def main():
    # Connect to Temporal
    client = await Client.connect("localhost:7233")

    # Create an instance of the activities class
    activities = ConfigApplyActivities()

    worker = Worker(
        client,
        task_queue="erpnext-apply-queue",
        workflows=[ConfigApplyWorkflow],
        activities=[
            activities.apply_erp_settings,
            activities.update_project_status
        ],
    )
    
    print("🚀 Config-Apply Worker is running...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())