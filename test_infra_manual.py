import asyncio
import logging
# Import your actual activity
from containers.erpnext_inventory.infra_agent.activities import deploy_inventory_container

# Mocking Temporal's logger so the script works without a Worker
class MockLogger:
    def info(self, msg): print(f"🔵 [INFO]: {msg}")
    def error(self, msg): print(f"🔴 [ERROR]: {msg}")

# Monkey-patch the activity logger
import containers.erpnext_inventory.infra_agent.activities as module_to_patch
module_to_patch.activity = type('obj', (object,), {'logger': MockLogger()})

async def run_test():
    print("🚀 Starting Smoke Test: Infra Agent...")

    # 1. Define the Input (What the Discovery Agent would usually send)
    test_payload = {
        "company_slug": "test-client-11",  # This will create test-client-03.f3next.in
        "tier": "standard"
    }

    try:
        # 2. Run the Activity Function directly
        print(f"📡 Connecting to EC2 to deploy {test_payload['company_slug']}...")
        result = await deploy_inventory_container(test_payload)

        # 3. Print the Result
        print("\n✅ DEPLOYMENT SUCCESSFUL!")
        print("-" * 30)
        print(f"🌍 Site URL:      {result['site_url']}")
        print(f"🔑 Admin Pass:    {result['erp_admin_password']}")
        print(f"🗄️ DB Root Pass:  {result['db_root_password']}")
        print(f"🖥️ Server IP:     {result['ip_address']}")
        print("-" * 30)
        print("👉 Go to the URL now. It might take 2-3 mins for ERPNext to boot.")

    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_test())