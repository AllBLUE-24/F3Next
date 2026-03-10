from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
# 🔴 NO activity imports here to prevent Sandbox Errors

@workflow.defn
class ConfigApplyWorkflow:
    @workflow.run
    async def run(self, project_id: str) -> str:
        # Step 1: Update DB Status
        await workflow.execute_activity(
            "update_project_status", 
            args=[project_id, "deployment_in_progress"],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Step 2: Apply Config (The heavy lifting)
        # The worker will use project_id to fetch inputs from PG
        await workflow.execute_activity(
            "apply_erp_settings", 
            args=[project_id],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3)        )

        # Step 3: Finalize Status
        await workflow.execute_activity(
            "update_project_status", 
            args=[project_id, "deployment_completed"],
            start_to_close_timeout=timedelta(seconds=10),
        )
        
        return f"Config applied for {project_id}"