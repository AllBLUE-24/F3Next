from datetime import timedelta
from temporalio import workflow

# Import activities from our local module
with workflow.unsafe.imports_passed_through():
    from containers.discovery.activities import (
        analyze_discovery_turn,
        save_discovery_state,
        generate_erp_recommendation,
        save_discovery_metadata,
    )

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
                    "message": bot_message,
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
                    "history": self._conversation_history,
                    "previous_question": bot_message,           # <-- ADDED: Passes context to prompt
                    "accumulated_tags": self._extracted_tags    # <-- ADDED: Passes context to prompt
                },
                start_to_close_timeout=timedelta(minutes=2)
            )
    
            # 4. Update State
            if analysis["status"] == "SUCCESS":
                # --- BULLETPROOF STEP ADVANCEMENT ---
                reported_next = analysis.get("next_step_id", self._current_step + 1)
                
                # If we are on Step 5, force it to Step 6 to break the loop!
                if self._current_step >= 5:
                    self._current_step = 6
                else:
                    # Make sure it actually moves forward and doesn't get stuck
                    self._current_step = reported_next if reported_next > self._current_step else self._current_step + 1
                # ------------------------------------
                
                # Combine and deduplicate tags correctly
                new_tags = analysis.get("extracted_tags", [])
                self._extracted_tags = list(set(self._extracted_tags + new_tags))
                
                self._conversation_history.append(f"User: {self._user_reply}")
                self._conversation_history.append(f"AI: {analysis.get('message', '')}")
                
                if self._current_step > 5:
                    self._is_complete = True
            
            bot_message = analysis.get("message", "One moment, please...")
            self._user_reply = None


        # Final step: Generate ERP recommendation + F3iche + Industry
        recommendation = await workflow.execute_activity(
            generate_erp_recommendation,
            self._extracted_tags, # Already a deduplicated list
            start_to_close_timeout=timedelta(minutes=2),
        )
        
        # This will now safely mark discovery_status="COMPLETE" in Postgres
        await workflow.execute_activity(
            save_discovery_metadata,
            {"project_id": project_id, "recommendation": recommendation},
            start_to_close_timeout=timedelta(seconds=10),
        )

        return {
            "status": "complete",
            "tags": self._extracted_tags,
            "f3iche": recommendation.get("f3iche", "trading"),
            "industry": recommendation.get("industry", ""),
            "recommended_erp": recommendation.get("recommended_erp"),
            "fit_score": recommendation.get("fit_score"),
        }