import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

import json
from temporalio.client import Client
from containers.os.execution_agent.workflows import ERPNextExecutionWorkflow

# ── THIS IS WHAT YOU MANUALLY WRITE FOR NOW ──────────────
payload = {
    "connection": {
        "site_url":   "https://tesla.f3next.in",
        "api_key":    "266a584707af136",
        "api_secret": "614824686c425c7"
    },
    "operation": {
        "type":    "create",
        "doctype": "Sales Order",
        "data": {
            "customer":       "Tesla Corp",
            "delivery_date":  "2026-03-20",
            "order_type":     "Sales",
            "items": [
                {
                    "item_code": "ITEM-001",
                    "qty": 2,
                    "rate": 500
                }
            ]
        }
    }
}
# ─────────────────────────────────────────────────────────

async def main():
    client = await Client.connect(os.getenv("TEMPORAL_HOST"))

    result = await client.execute_workflow(
        ERPNextExecutionWorkflow.run,
        payload,
        id="exec-sales-order-001",
        task_queue="erpnext-execution-queue"
    )

    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
