import asyncio
from sqlalchemy.future import select
from temporalio.client import Client

# 1. Import your actual DB and Models (Dynamic Data)
from shared.database.db import AsyncSessionLocal 
from shared.models.core import Project, Client as DbClient

async def main():
    # --- CONFIGURATION (What are we looking for?) ---
    # We look up the project by the User's Firebase UID (since that's what you have in auth)
    # OR by the Container ID if you map that in your DB.
    
    TARGET_FIREBASE_UID = "4J3e1KHrOCeZt7Be2mL8OfNZsf42" # <--- The user ID from your logs/auth
    CONTAINER_ID = "cnt_stock_109"
    WORKFLOW_ID = f"config-workflow-{CONTAINER_ID}"

    print(f"🔍 Looking up Project for User: {TARGET_FIREBASE_UID}...")

    # 2. Fetch the REAL Project ID from Database
    project_id_uuid = None
    
    async with AsyncSessionLocal() as session:
        # Query Projects table where client_id matches the Firebase UID
        stmt = select(Project).where(Project.client_id == TARGET_FIREBASE_UID)
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            print("❌ ERROR: No Project found for this user in the DB!")
            print("   (Ensure the user has created a project via the Onboarding flow first)")
            return
            
        project_id_uuid = str(project.id) # Convert UUID object to string
        print(f"✅ Found Valid Project UUID: {project_id_uuid}")
        print(f"   (Linked to Company: {project.company_name})")

    # 3. Connect to Temporal and Start Workflow with REAL ID
    client = await Client.connect("localhost:7233")
    
    # Terminate existing zombie if running
    try:
        handle = client.get_workflow_handle(WORKFLOW_ID)
        await handle.terminate("Restarting with valid UUID")
        print("💀 Terminated old workflow.")
    except Exception:
        pass # It wasn't running

    print(f"🚀 Starting Workflow {WORKFLOW_ID}...")
    
    initial_tags = ["#Ind_Manufacturing", "#Scale_SMB"] # (You can also fetch these from DB if stored)

    try:
        handle = await client.start_workflow(
            "ConfigWorkflow",
            # 🔴 PASSING THE REAL DB UUID HERE
            args=[CONTAINER_ID, project_id_uuid, initial_tags], 
            id=WORKFLOW_ID,
            task_queue="erpnext-inventory-queue"
        )
        print(f"✅ Success! Workflow started with RunID: {handle.result_run_id}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())