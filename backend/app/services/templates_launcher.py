from temporalio.client import Client

TEMPORAL_HOST = "localhost:7233"

async def start_template_agent(project_id: str, config_data: dict) -> str:
    """
    Connects to Temporal and starts the TemplateGenWorkflow.
    """
    print(f"[Templates] Starting Template Agent for project {project_id}...")
    client = await Client.connect(TEMPORAL_HOST)

    handle = await client.start_workflow(
        "TemplateGenWorkflow",
        args=[project_id, config_data],
        id=f"template-{project_id}",
        task_queue="erpnext-template-queue"
    )
    return handle.result_run_id