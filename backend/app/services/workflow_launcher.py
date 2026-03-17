from temporalio.client import Client
import uuid

class WorkflowLauncher:
    def __init__(self, temporal_url="localhost:7233"):
        self.temporal_url = temporal_url

    async def launch_agent(self, workflow_name: str, project_id: str, task_queue: str, **kwargs):
        """
        The Universal Forwarder: Ensures project_id is ALWAYS the first argument
        sent to any workflow launcher.
        """
        client = await Client.connect(self.temporal_url)
        
        # We enforce that project_id is always passed to the workflow
        workflow_id = f"{workflow_name.lower()}-{project_id}"
        
        await client.start_workflow(
            workflow_name,
            args=[project_id, *kwargs.values()],
            id=workflow_id,
            task_queue=task_queue
        )
        return workflow_id

# Global instance for the backend to use
launcher = WorkflowLauncher()