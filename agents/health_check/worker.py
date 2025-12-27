import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from agents.health_check.workflows import HealthCheckWorkflow
from agents.health_check.activities import (
    analyze_health_logic, 
    generate_health_report,
    save_report_to_db  # <--- Ensure this is imported!
)
from agents.health_check.workflows import HealthCheckWorkflow

async def main():
    # connect to temporal
    client = await Client.connect("127.0.0.1:7233") # Connects to the docker service if localhost/127.0.0.1 --> temporal
    # 2. Register ALL activities with the worker
    worker = Worker(
        client,
        task_queue="health-check-queue",
        workflows=[HealthCheckWorkflow],
        activities=[analyze_health_logic, generate_health_report, save_report_to_db]
    )
    print("🚀 F3Next Health-Check Worker is LIVE and listening...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())