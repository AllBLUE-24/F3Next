import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

# Import the actual implementations
from containers.erpnext_inventory.infra_agent.activities import deploy_inventory_container, generate_erpnext_keys, save_deployment_details
from containers.erpnext_inventory.infra_agent.workflows import ERPNextProvisioningWorkflow

async def main():
    # 1. Connect to Temporal Server (Localhost for now)
    client = await Client.connect("localhost:7233")

    # 2. Define the Worker
    # 'task_queue' must match what you use when starting the workflow
    worker = Worker(
        client,
        task_queue="erpnext-provisioning-queue",
        workflows=[ERPNextProvisioningWorkflow],
        activities=[deploy_inventory_container,generate_erpnext_keys, save_deployment_details],
    )

    print("👷 Infra Worker started... Waiting for tasks.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())