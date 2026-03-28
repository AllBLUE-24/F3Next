from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from containers.os.execution_agent.activities import (
        validate_payload,
        execute_erpnext_operation,
        save_execution_log
    )

@workflow.defn
class ERPNextExecutionWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> dict:
        workflow.logger.info(f"⚡ Execution started for {payload['operation']['doctype']}")

        # STEP 1 — Validate first, fail fast
        validated = await workflow.execute_activity(
            validate_payload,
            payload,
            start_to_close_timeout=timedelta(seconds=10)
        )

        # STEP 2 — Fire the actual ERPNext call
        result = await workflow.execute_activity(
            execute_erpnext_operation,
            validated,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )

        # STEP 3 — Log it
        await workflow.execute_activity(
            save_execution_log,
            {
                "site_url":  payload["connection"]["site_url"],
                "operation": payload["operation"]["type"],
                "doctype":   payload["operation"]["doctype"],
                "result":    result
            },
            start_to_close_timeout=timedelta(seconds=10)
        )

        workflow.logger.info("✅ Execution Complete!")
        return result