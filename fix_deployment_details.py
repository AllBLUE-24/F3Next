"""
Fix: Use site_url as erp_url (it has the correct full hostname).
"""
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv('c:/dev/F3Next/.env')

async def main():
    url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql')
    conn = await asyncpg.connect(url, statement_cache_size=0)

    rows = await conn.fetch(
        "SELECT id, company_slug, deployment_details FROM projects WHERE deployment_details IS NOT NULL"
    )

    patched = 0
    for row in rows:
        details = json.loads(row['deployment_details']) if isinstance(row['deployment_details'], str) else row['deployment_details']
        if not details:
            continue

        site_url = details.get("site_url", "")
        current_erp_url = details.get("erp_url", "")

        # If site_url exists and erp_url is wrong (doesn't have .f3next.in), fix it
        if site_url and (not current_erp_url or ".f3next.in" not in current_erp_url):
            details["erp_url"] = site_url
            await conn.execute(
                "UPDATE projects SET deployment_details = $1::jsonb WHERE id = $2",
                json.dumps(details), row['id']
            )
            print(f"✅ Fixed {row['company_slug']}: erp_url = {details['erp_url']}")
            patched += 1
        else:
            print(f"⏭️  {row['company_slug']}: erp_url={current_erp_url} (OK)")

    print(f"\nDone. Fixed {patched} project(s).")
    await conn.close()

asyncio.run(main())
