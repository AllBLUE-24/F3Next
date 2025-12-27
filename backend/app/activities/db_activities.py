from temporalio import activity
from app.models.core import Project
# ... other imports

@activity.defn
async def update_project_status(data: dict):
    # This logic was previously inside your health_check_service.py
    # Now it's a reusable activity for any agent
    uid = data["uid"]
    status = data["status"]
    # Logic to update Postgres goes here...
    return True
    