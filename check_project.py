import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv('c:/dev/F3Next/.env')

async def main():
    try:
        url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql')
        conn = await asyncpg.connect(url, statement_cache_size=0)
        
        row = await conn.fetchrow(
            "SELECT id, company_name, company_slug, deployment_details FROM projects WHERE company_slug = 'vindhya-spices-preserves';"
        )
        
        if row:
            print("Project Found:")
            print(f"ID: {row['id']}")
            print(f"Company: {row['company_name']}")
            print(f"Slug: {row['company_slug']}")
            details = row['deployment_details']
            if details:
                parsed = json.loads(details)
                print(json.dumps(parsed, indent=2))
            else:
                print("deployment_details is None")
        else:
            print("Project 'vindhya-spices-preserves' not found!")
            
        await conn.close()
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
