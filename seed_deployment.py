"""
seed_deployment.py

One-time script to wire a deployed ERPNext site's credentials
into the projects table so the OS pipeline uses real ERP instead of the stub.

Run this ONCE per project after ERPNext is deployed:
  python seed_deployment.py

What it does:
  UPDATE projects
  SET deployment_details = {...}
  WHERE company_slug = 'tesla'

After running this, the OS pipeline will:
  - Pull real erp_url + api_key + api_secret from DB
  - Fire actual REST calls against tesla.f3next.in
  - Return real document names like "SAL-2026-00001"
  - Show a real link in the UI
"""

import asyncio
import json
import sys
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import update, select, text
from shared.database.db import AsyncSessionLocal
from shared.models.core import Project, ProjectStatus


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURE THESE PER PROJECT
# ══════════════════════════════════════════════════════════════════════════════

DEPLOYMENTS = [
    {
        # The company_slug value in the projects table
        "company_slug": "tesla",

        # The ERPNext site URL (must be reachable from the OS worker)
        "erp_url": "https://tesla.f3next.in",

        # API Key + Secret for the Administrator user
        # (from infra_agent generate_erpnext_keys output, or manually from ERPNext UI)
        "api_key":    "266a584707af136",
        "api_secret": "614824686c425c7",

        # Default company name inside ERPNext (Settings → Company)
        "company": "Tesla",

        # Container ID (informational — used for infra management)
        "container_id": "cnt_tesla",
    },
    # Add more projects here as they get deployed:
    # {
    #     "company_slug": "f3",
    #     "erp_url": "https://f3.f3next.in",
    #     "api_key": "...",
    #     "api_secret": "...",
    #     "company": "F3 Company",
    #     "container_id": "cnt_f3",
    # },
]

# ══════════════════════════════════════════════════════════════════════════════


async def seed(deployment: dict) -> None:
    slug = deployment["company_slug"]

    # Shape that company_profile.py expects to read from deployment_details
    details = {
        "erp_url":      deployment["erp_url"],
        "api_key":      deployment["api_key"],
        "api_secret":   deployment["api_secret"],
        "company":      deployment.get("company", ""),
        "container_id": deployment.get("container_id", f"cnt_{slug}"),
    }

    print(f"\n{'='*60}")
    print(f"  Seeding: {slug}")
    print(f"  ERP URL: {details['erp_url']}")
    print(f"  API Key: {details['api_key'][:8]}...")
    print(f"{'='*60}")

    async with AsyncSessionLocal() as session:
        async with session.begin():

            # 1. Find the project
            result = await session.execute(
                select(Project).where(Project.company_slug == slug)
            )
            project = result.scalar_one_or_none()

            if project is None:
                print(f"  ❌ Project '{slug}' not found in projects table.")
                print(f"     Make sure the company_slug matches exactly.")
                return

            print(f"  Found project: id={project.id}  name={project.company_name}")
            print(f"  Current deployment_details: {json.dumps(project.deployment_details, indent=2) if project.deployment_details else 'NULL'}")

            # 2. Update deployment_details
            stmt = (
                update(Project)
                .where(Project.company_slug == slug)
                .values(
                    deployment_details=details,
                    status=ProjectStatus.DEPLOYMENT_COMPLETED,
                )
            )
            await session.execute(stmt)

    print(f"\n  ✅ deployment_details saved for '{slug}'")
    print(f"     The OS pipeline will now use real ERPNext at {details['erp_url']}")
    print(f"\n  Restart the OS worker for changes to take effect:")
    print(f"     python -m containers.os.os_worker")


async def verify(slug: str) -> None:
    """Read back the saved details to confirm."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT company_slug, company_name, deployment_details, status
                FROM projects
                WHERE company_slug = :slug
            """),
            {"slug": slug},
        )
        row = result.mappings().first()
        if row:
            details = row["deployment_details"] or {}
            print(f"\n  Verification:")
            print(f"    company_slug:  {row['company_slug']}")
            print(f"    company_name:  {row['company_name']}")
            print(f"    status:        {row['status']}")
            print(f"    erp_url:       {details.get('erp_url', '—')}")
            print(f"    api_key:       {str(details.get('api_key', '—'))[:8]}...")
            print(f"    api_secret:    {'SET' if details.get('api_secret') else 'MISSING'}")


async def main() -> None:
    print("F3Next — Deployment Seeder")
    print(f"Seeding {len(DEPLOYMENTS)} project(s)...")

    for deployment in DEPLOYMENTS:
        await seed(deployment)
        await verify(deployment["company_slug"])

    print(f"\n{'='*60}")
    print("Done. Your OS pipeline is now wired to real ERPNext.")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())