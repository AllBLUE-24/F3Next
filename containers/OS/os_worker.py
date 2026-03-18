import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# ─── Clean Terminal Logging ───────────────────────────────────────────────────
# Suppress raw SQL queries and internal Temporal background warnings
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("temporalio.worker").setLevel(logging.ERROR)

# All your existing activities
from containers.OS.clarity_agent.activities import extract_intent, resolve_ambiguity
from containers.OS.context_retrieval.activities import retrieve_context
from containers.OS.command_planner.activities import plan_command
from containers.OS.payload_generator.activities import generate_payload
from containers.OS.validation_agent.activities import validate_payload
from containers.OS.execution_agent.activities import execute_command
from containers.OS.result_formatter.activities import format_result
from containers.OS.os_workflow.workflow import ERPOSCommandWorkflow
from containers.OS.search_planner.activities import plan_search

async def main():
    client = await Client.connect("localhost:7233")

    activities_list = [
        extract_intent, resolve_ambiguity, retrieve_context,
        plan_command, generate_payload, validate_payload, 
        execute_command, format_result, plan_search
    ]

    # Worker 1: Main Router Queue (Workflow + Clarity/Context)
    worker_main = Worker(
        client,
        task_queue="os-main-queue",
        workflows=[ERPOSCommandWorkflow],
        activities=activities_list,
    )

    # Worker 2: Execute Heavy Lifting Queue
    worker_execute = Worker(
        client,
        task_queue="os-execute-queue",
        activities=activities_list, 
    )

    # Future Workers (Search & Analyze)
    worker_search = Worker(client, task_queue="os-search-queue", activities=activities_list)
    worker_analyze = Worker(client, task_queue="os-analyze-queue", activities=activities_list)

    print("\n┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print("┃                 F3NEXT ERP-OS MULTI-QUEUE                   ┃")
    print("┠─────────────────────────────────────────────────────────────┨")
    print("┃  [1] os-main-queue      (Router & Clarity/Context)          ┃")
    print("┃  [2] os-execute-queue   (Standard ERP Writes)               ┃")
    print("┃  [3] os-search-queue    (Read-Only Data Fetching)           ┃")
    print("┃  [4] os-analyze-queue   (Data Aggregation & AI Analysis)    ┃")
    print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    print("🟢 All queues live and waiting for commands...\n")
    
    await asyncio.gather(
        worker_main.run(),
        worker_execute.run(),
        worker_search.run(),
        worker_analyze.run()
    )

if __name__ == "__main__":
    asyncio.run(main())