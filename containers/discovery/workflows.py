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
        
        # Initial greeting if no message exists
        bot_message = "Welcome to F3Next Discovery. Let's start with your industry: What does your company manufacture or trade?"
        
        while not self._is_complete:
            # 1. Update the DB so the Frontend can see the latest question
            await workflow.execute_activity(
                save_discovery_state,
                {
                    "project_id": project_id,
                    "bot_response": bot_message,
                    "step": self._current_step,
                    "tags": self._extracted_tags
                },
                start_to_close_timeout=timedelta(seconds=10)
            )

            # 2. Wait for the user to reply via the Signal
            await workflow.wait_condition(lambda: self._user_reply is not None)
            
            # 3. Process the answer with the LLM Activity
            analysis = await workflow.execute_activity(
                analyze_discovery_turn,
                {
                    "user_answer": self._user_reply,
                    "current_step": self._current_step,
                    "history": self._conversation_history
                },
                start_to_close_timeout=timedelta(minutes=2)
            )

            # 4. Handle LLM Result
            if analysis["status"] == "SUCCESS":
                self._current_step = analysis["next_step_id"]
                self._extracted_tags.extend(analysis["extracted_tags"])
                # Log history for context-awareness in the next turn
                self._conversation_history.append(f"User: {self._user_reply}")
                self._conversation_history.append(f"AI: {analysis['bot_response']}")
                
                # Check if we have hit the final step (Step 5)
                if self._current_step > 5:
                    self._is_complete = True
            
            bot_message = analysis["bot_response"]
            self._user_reply = None # Reset and wait for next signal

        return {"status": "complete", "tags": list(set(self._extracted_tags))}