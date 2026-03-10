import asyncio
from containers.ERPNext.infra_agent.activities import generate_erpnext_keys

# Mock Logger (so it doesn't crash)
class MockLogger:
    def info(self, msg): print(f"🔵 [INFO]: {msg}")
    def error(self, msg): print(f"🔴 [ERROR]: {msg}")

import containers.ERPNext.infra_agent.activities as module_to_patch
module_to_patch.activity = type('obj', (object,), {'logger': MockLogger()})

async def test_keygen_only():
    print("🧪 Testing API Key Generation (Skipping Deployment)...")

    # 1. MOCK INPUT 
    # Use the details of the site that is CURRENTLY running on your EC2.
    # Check your recent logs to see which slug was used (e.g., test-client-14).
    slug = "middle-ground" 
    
    mock_input = {
        "infrastructure": {
            "ip_address": "65.2.125.86", # Your EC2 IP
            "ssh_user": "ubuntu",
            "base_dir": f"/opt/erp/clients/{slug}", 
            "site_url": f"{slug}.f3next.in"
        }
    }

    try:
        # 2. CALL ACTIVITY DIRECTLY
        print(f"🔑 Attempting to generate keys for {slug}...")
        result = await generate_erpnext_keys(mock_input)

        print("\n✅ SUCCESS!")
        print(f"API Key:    {result['api_key']}")
        print(f"API Secret: {result['api_secret']}")

    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_keygen_only())