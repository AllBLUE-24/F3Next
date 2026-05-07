import asyncio
from containers.context_versioning.snapshot_builder.erp_fetcher import fetch_master_data

async def run_test():
    profile = {
        "erp_url": "https://f3.f3next.app",
        "api_key": "9010a11e121bc04",
        "api_secret": "da37e07102debc8",
        "company_name": "F3Next",
        "allow_insecure_ssl": True
    }
    
    print("Testing ERPNext fetcher...")
    try:
        data = await fetch_master_data(profile)
        print("\nSUCCESS! Fetched counts:")
        print(data.get("counts"))
    except Exception as e:
        print(f"\nFETCH FAILED LOUDLY AS EXPECTED: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
