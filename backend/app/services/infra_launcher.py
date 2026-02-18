import asyncio
import sys
import os

# Add the parent directory to path so we can import workflows
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio.client import Client

async def main():
    # 1. Connect to Temporal Server
    client = await Client.connect("localhost:7233")

    # 2. Prepare the Input Data (Simulating what Discovery Agent sends)
    # 💡 CHANGE THIS SLUG to test a new deployment (e.g., test-client-19)
    input_data = {
        "project_id": "proj_001_acme",
        "company_slug": "test-client-19", 
        "tier": "standard"
    }

    print(f"🚀 Triggering Infra Workflow for {input_data['company_slug']}...")

    # 3. Start the Workflow
    # This doesn't run the code locally. It pushes a task to the Queue.
    handle = await client.start_workflow(
        "ERPNextProvisioningWorkflow", # Must match the class name in workflows.py
        input_data,
        id=f"provision-{input_data['company_slug']}", # Unique ID prevents duplicate runs
        task_queue="erpnext-provisioning-queue",
    )

    print(f"✅ Workflow Submitted! ID: {handle.id}")
    print(f"👉 Now check your Terminal running 'worker.py'")
    print(f"👉 Check the UI at http://localhost:8233")

    # Optional: Wait for the result (blocks until finished)
    # result = await handle.result()
    # print(f"🏁 Workflow Finished! Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())