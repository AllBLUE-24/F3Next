import asyncio
import sys
import os
from dotenv import load_dotenv
load_dotenv()


# Add the parent directory to path so we can import workflows
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio.client import Client

async def main():
    # 1. Connect to Temporal Server
    client = await Client.connect(os.getenv("TEMPORAL_HOST"))

    # 2. Prepare the Input Data (Simulating what Discovery Agent sends)
    # 💡 CHANGE THIS SLUG to test a new deployment (e.g., test-client-19)
    input_data = {
        "project_id": "proj_001_acme",
        "company_slug": "test-client-19", 
        "tier": "standard"
    }

    print(f"[Infra] Triggering workflow for {input_data['company_slug']}...")

    # 3. Start the Workflow
    # This doesn't run the code locally. It pushes a task to the Queue.
    handle = await client.start_workflow(
        "ERPNextProvisioningWorkflow", # Must match the class name in workflows.py
        input_data,
        id=f"provision-{input_data['company_slug']}", # Unique ID prevents duplicate runs
        task_queue="erpnext-provisioning-queue",
    )

    print(f"✅ Workflow Submitted! ID: {handle.id}")
    ui_url = os.getenv("TEMPORAL_UI_URL", "http://localhost:8080")
    print(f"Check the terminal running the infra worker and the UI at {ui_url}")

    # Optional: Wait for the result (blocks until finished)
    # result = await handle.result()
    # print(f"🏁 Workflow Finished! Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())