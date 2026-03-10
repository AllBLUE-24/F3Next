import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from containers.discovery.workflows import DiscoveryChatWorkflow
from containers.discovery.activities import analyze_discovery_turn, save_discovery_state

async def main():
    client = await Client.connect("127.0.0.1:7233")
    worker = Worker(
        client,
        task_queue="discovery-queue", # Isolated from health-check
        workflows=[DiscoveryChatWorkflow],
        activities=[analyze_discovery_turn, save_discovery_state],
    )
    print("🤖 Discovery Agent Container: Online & Listening...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())