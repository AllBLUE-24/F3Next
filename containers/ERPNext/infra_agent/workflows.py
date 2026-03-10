from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import your activities definition (interface only)
# 💡 FIX: Removed 'infra_result' from the import list
with workflow.unsafe.imports_passed_through():
    from containers.ERPNext.infra_agent.activities import (
        deploy_inventory_container, 
        save_deployment_details, 
        generate_erpnext_keys
    )

@workflow.defn
class ERPNextProvisioningWorkflow:
    @workflow.run
    async def run(self, input_data: dict) -> dict:
        workflow.logger.info(f"🚀 Starting Provisioning for {input_data.get('project_id')}")

        # ---------------------------------------------------------
        # STEP 1: Deploy the Container (The Heavy Lifting)
        # ---------------------------------------------------------
        # We set a high timeout (20 mins) because building/installing takes time.
        deploy_result = await workflow.execute_activity(
            deploy_inventory_container,
            input_data,
            start_to_close_timeout=timedelta(minutes=20),
            retry_policy=RetryPolicy(maximum_attempts=2) # Don't infinite retry expensive ops
        )

        # ---------------------------------------------------------
        # STEP 2: Generate Keys (The Fragile Part)
        # ---------------------------------------------------------
        # 💡 FIX: We pass 'deploy_result' (Output of Step 1) as input here.
        keys_result = await workflow.execute_activity(
            generate_erpnext_keys,
            deploy_result, 
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=5) # Retry 5 times if site is slow
        )

        # ---------------------------------------------------------
        # STEP 3: Save to DB (The Handoff)
        # ---------------------------------------------------------
        # Combine the data for the final save
        save_input = {
            "project_id": input_data["project_id"],
            "deployment_details": {
                "site_url": keys_result["site_url"],
                "api_key": keys_result["api_key"],
                "api_secret": keys_result["api_secret"],
                "container_id": f"cnt_{input_data.get('company_slug')}"
            }
        }

        await workflow.execute_activity(
            save_deployment_details,
            save_input,
            start_to_close_timeout=timedelta(minutes=2)
        )

        workflow.logger.info("✅ Provisioning Complete!")
        
        return {
            "status": "completed", 
            "site_url": keys_result["site_url"]
        }