from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from containers.discovery.activities import (
        analyze_discovery_turn,
        save_discovery_state,
        generate_erp_recommendation,
        save_discovery_metadata,
        EMPTY_COVERAGE,
        MAX_TURNS,
        _coverage_is_complete,
    )

@workflow.defn
class DiscoveryChatWorkflow:
    def __init__(self):
        self._user_reply          = None
        self._is_complete         = False
        self._coverage            = dict(EMPTY_COVERAGE)   # tracks understanding per dimension
        self._extracted_tags      = []
        self._conversation_history= []
        self._turn_count          = 0

    @workflow.signal
    def receive_user_reply(self, message: str):
        """Gateway for the backend to talk to this workflow."""
        self._user_reply = message

    @workflow.run
    async def run(self, data: dict) -> dict:
        project_id = data.get("project_id")

        # -------------------------------------------------------
        # Opening message — Adi introduces herself naturally
        # -------------------------------------------------------
        bot_message = (
            "Hey — I'm Adi. I help businesses figure out the right ERP setup. "
            "What does your company do?"
        )

        while not self._is_complete:

            # 1. Persist current bot message to DB (so frontend can poll and display it)
            await workflow.execute_activity(
                save_discovery_state,
                {
                    "project_id":  project_id,
                    "message":     bot_message,
                    "step":        self._turn_count + 1,
                    "tags":        self._extracted_tags,
                    "coverage":    self._coverage,
                    "turn_count":  self._turn_count,
                    "is_complete": False,
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            # 2. Wait for the user to reply
            await workflow.wait_condition(lambda: self._user_reply is not None)

            # 3. Analyze the reply with full coverage context
            analysis = await workflow.execute_activity(
                analyze_discovery_turn,
                {
                    "user_answer":          self._user_reply,
                    "current_coverage":     self._coverage,
                    "accumulated_tags":     self._extracted_tags,
                    "conversation_history": self._conversation_history,
                    "turn_count":           self._turn_count,
                },
                start_to_close_timeout=timedelta(minutes=2),
            )

            # 4. Update workflow state
            if analysis.get("status") == "SUCCESS":
                updated_cov = analysis.get("updated_coverage", self._coverage)
                self._coverage = updated_cov

                new_tags = analysis.get("extracted_tags", [])
                self._extracted_tags = list(set(self._extracted_tags + new_tags))

                self._conversation_history.append(f"User: {self._user_reply}")
                self._conversation_history.append(f"Adi: {analysis.get('message', '')}")
                if len(self._conversation_history) > 16:
                    self._conversation_history = self._conversation_history[-16:]

                self._turn_count += 1

                # Programmatic check is the SOLE gatekeeper — never trust LLM's is_complete
                if _coverage_is_complete(self._coverage, self._turn_count):
                    self._is_complete = True

            # 5. Prepare next bot message and clear reply slot
            bot_message      = analysis.get("message", "Could you say that again?")
            self._user_reply = None

            # 6. IMMEDIATELY save Adi's response to DB so frontend sees it right away
            #    (don't wait until next loop iteration — that causes the "Adi is thinking" stall)
            await workflow.execute_activity(
                save_discovery_state,
                {
                    "project_id":  project_id,
                    "message":     bot_message,
                    "step":        self._turn_count + 1,
                    "tags":        self._extracted_tags,
                    "coverage":    self._coverage,
                    "turn_count":  self._turn_count,
                    "is_complete": self._is_complete,
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

        # -------------------------------------------------------
        # Final recommendation (runs after the conversation loop)
        # -------------------------------------------------------
        recommendation = await workflow.execute_activity(
            generate_erp_recommendation,
            {
                "tags":     self._extracted_tags,
                "coverage": self._coverage,
            },
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Persist final state — marks discovery_status = "COMPLETE"
        await workflow.execute_activity(
            save_discovery_metadata,
            {
                "project_id":     project_id,
                "recommendation": recommendation,
                "coverage":       self._coverage,
            },
            start_to_close_timeout=timedelta(seconds=10),
        )

        return {
            "status":           "complete",
            "tags":             self._extracted_tags,
            "coverage":         self._coverage,
            "turn_count":       self._turn_count,
            "f3iche":           recommendation.get("f3iche", "trading"),
            "industry":         recommendation.get("industry", ""),
            "recommended_erp":  recommendation.get("recommended_erp"),
            "fit_score":        recommendation.get("fit_score"),
        }