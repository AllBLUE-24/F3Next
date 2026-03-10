import asyncio
import os
from temporalio.client import Client
from dotenv import load_dotenv

load_dotenv()

# WORKFLOW_ID must match the running workflow in your logs
WORKFLOW_ID = "migration-middle-ground-89132f48-00f0-4145-ad41-c9867bb949ed"

async def main():
    client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
    
    SIGNAL_NAME = "submit_mapping_correction"
    
    # --- CORRECTED MAPPING ---
    # Keys must match YOUR FILE (left side)
    # Values must match ERPNEXT FIELDS (right side)
    approved_mapping = {
        "Company Name": "customer_name",
        "Phone_WhatsApp": "mobile_no",
        "Email": "email_id",
        "Location": "territory"
        # Add other fields if needed, or leave them out to ignore them
    }

    print(f"Sending signal to workflow: {WORKFLOW_ID}...")
    
    await client.get_workflow_handle(WORKFLOW_ID).signal(
        SIGNAL_NAME, 
        approved_mapping
    )
    
    print("Signal sent! Check the Temporal UI/Worker logs.")

if __name__ == "__main__":
    asyncio.run(main())