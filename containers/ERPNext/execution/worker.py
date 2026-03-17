import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from containers.ERPNext.execution.activities import (
    validate_payload,
    execute_erpnext_operation,
    save_execution_log
)
from containers.ERPNext.execution.workflows import ERPNextExecutionWorkflow

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="erpnext-execution-queue",   # different queue from infra agent
        workflows=[ERPNextExecutionWorkflow],
        activities=[validate_payload, execute_erpnext_operation, save_execution_log],
    )

    print("⚡ Execution Worker started... Waiting for tasks.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())