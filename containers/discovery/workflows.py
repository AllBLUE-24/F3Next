from datetime import timedelta
from temporalio import workflow

# Import activities from our local module
with workflow.unsafe.imports_passed_through():
    from containers.discovery.activities import analyze_discovery_turn, save_discovery_state

@workflow.defn
class DiscoveryChatWorkflow:
    def __init__(self):
        self._user_reply = None
        self._is_complete = False
        self._current_step = 1
        self._extracted_tags = []
        self._conversation_history = []

    @workflow.signal
    def receive_user_reply(self, message: str):
        """This is the gateway for the Backend to talk to this container"""
        self._user_reply = message

    @workflow.run
    async def run(self, data: dict) -> dict:
        project_id = data.get("project_id")
        
        # Initial greeting
        bot_message = "Welcome to F3Next Discovery. Let's start with your industry: What does your company manufacture or trade?"
        
        while not self._is_complete:
            # 1. Update DB
            await workflow.execute_activity(
                save_discovery_state,
                {
                    "project_id": project_id,
                    "message": bot_message, # Changed key to 'message' to match activity
                    "step": self._current_step,
                    "tags": self._extracted_tags
                },
                start_to_close_timeout=timedelta(seconds=10)
            )
    
            # 2. Wait for user
            await workflow.wait_condition(lambda: self._user_reply is not None)
            
            # 3. Analyze
            analysis = await workflow.execute_activity(
                analyze_discovery_turn,
                {
                    "user_answer": self._user_reply,
                    "current_step": self._current_step,
                    "history": self._conversation_history
                },
                start_to_close_timeout=timedelta(minutes=2)
            )
    
            # 4. Update State
            if analysis["status"] == "SUCCESS":
                self._current_step = analysis["next_step_id"]
                self._extracted_tags.extend(analysis.get("extracted_tags", []))
                self._conversation_history.append(f"User: {self._user_reply}")
                self._conversation_history.append(f"AI: {analysis['message']}")
                
                if self._current_step > 5:
                    self._is_complete = True
            
            # Use the 'message' field we ensured exists in activity
            bot_message = analysis.get("message", "One moment, please...")
            self._user_reply = None 
    
        return {"status": "complete", "tags": list(set(self._extracted_tags))}