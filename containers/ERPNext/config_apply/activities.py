from temporalio import activity
# 🟢 FIX: Import ApplicationError
from temporalio.exceptions import ApplicationError 
import httpx
from sqlalchemy import select, update
from shared.database.db import AsyncSessionLocal as async_session
from shared.models.core import Project

class ConfigApplyActivities:
    @activity.defn
    async def apply_erp_settings(self, project_id: str) -> bool:
        async with async_session() as session:
            result = await session.execute(select(Project).filter(Project.id == project_id))
            project = result.scalars().first()
            if not project: raise ValueError(f"Project {project_id} not found")

            config = project.processed_config
            deployment = project.deployment_details
            
            erp_url = deployment.get("site_url")
            api_key = deployment.get("api_key")
            api_secret = deployment.get("api_secret")

            if not api_key or not api_secret:
                raise ValueError("Deployment details missing API Key/Secret")

            async with httpx.AsyncClient(verify=False) as client:
                print(f"🚀 Sending Config to: {erp_url}/api/method/f3next.api.apply_config")
                
                # 🟡 DEBUG: Check if your config is a List or a Dict
                print(f"Payload Type: {type(config)}") 

                try:
                    # 🟢 CRITICAL: Frappe usually expects a named argument.
                    # If 'config' is a list, we likely need to wrap it.
                    # We try sending it wrapped in 'data' which is a common Frappe convention.
                    payload = {"data": config} 

                    response = await client.post(
                        f"{erp_url}/api/method/f3next.api.apply_config",
                        json=payload, 
                        headers={"Authorization": f"token {api_key}:{api_secret}"},
                        timeout=60.0
                    )
                    
                    # 🔴 DEBUG: Print the ERROR details if it fails
                    if response.status_code >= 400:
                        print(f"❌ ERPNext API Error ({response.status_code}):")
                        print(f"Response Body: {response.text}") 

                    response.raise_for_status()

                except httpx.HTTPStatusError as e:
                    # Now this will work because we imported ApplicationError
                    raise ApplicationError(f"ERPNext Rejected Config: {e.response.text}") from e
            
            return True

    @activity.defn
    async def update_project_status(self, project_id: str, status: str):
        async with async_session() as session:
            await session.execute(
                update(Project).where(Project.id == project_id).values(status=status)
            )
            await session.commit()