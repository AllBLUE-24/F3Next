from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy 

# Define a strict retry policy for LLM calls
llm_retry_policy = RetryPolicy(
    initial_interval=timedelta(minutes=1), # Wait a full minute before retrying
    backoff_coefficient=3.0,
    maximum_interval=timedelta(minutes=10),
    maximum_attempts=10,                 # Wait 60s, then 120s, then 240s
)

with workflow.unsafe.imports_passed_through():
    from containers.health_check.activities import (
        analyze_health_logic,
        generate_health_report,
        save_report_to_db
    )

@workflow.defn
class HealthCheckWorkflow:
    @workflow.run
    async def run(self, data: dict) -> str:

        # Activity 1: Logic
        analysis = await workflow.execute_activity(
            "analyze_health_logic",
            data,
            start_to_close_timeout=timedelta(minutes=1)
        )

        # Activity 2: Report (With the new Retry Policy)
        report = await workflow.execute_activity(
            "generate_health_report",
            analysis,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=llm_retry_policy # This saves your quota!
        )

        # Activity 3: Final Save to Database
        # We pass both the report and the original project_id
        project_id = data.get("project_id")

        await workflow.execute_activity(
        save_report_to_db,
        {
            "project_id": project_id, # Ensure this key exists!
            "report": report
        },
        start_to_close_timeout=timedelta(seconds=30)
    )
    
        return report
