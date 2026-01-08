from temporalio import workflow
from datetime import timedelta
from typing import List, Dict, Any

# Import your activity definitions here so the workflow knows their names
# (Note: In Temporal, you often pass activity names as strings, but having this comment helps)

@workflow.defn
class ConfigWorkflow:
    def __init__(self):
        self.project_id = None
        self.current_tags = []
        self.current_layer = 1
        self.answers_received = False
        self.latest_answers = {}
        self.config_accumulator = {}
        self.current_questions = []
        self.status = "STARTING"

    @workflow.query
    def get_state(self):
        return {
            "status": self.status,
            "layer": self.current_layer,
            "questions": self.current_questions,
            "tags": self.current_tags
        }

    @workflow.signal
    def submit_answers_signal(self, answers: Dict[str, Any]):
        self.latest_answers = answers
        self.answers_received = True

    @workflow.run
    async def run(self, container_id: str, project_id: str, initial_tags: List[str]):
        # 1. Initialize State
        self.project_id = project_id
        self.current_tags = initial_tags
        self.status = "IN_PROGRESS"

        # 2. Loop through Layers 1 to 4
        for layer in range(1, 5):
            self.current_layer = layer
            self.answers_received = False
            
            # A. Fetch Questions for this layer
            self.current_questions = await workflow.execute_activity(
                "fetch_layer_questions",
                args=[layer, self.current_tags],
                start_to_close_timeout=timedelta(seconds=10)
            )

            # Check if there are questions (skip layer if empty)
            if not self.current_questions:
                continue

            await workflow.sleep(1)

            # B. Wait for User Signal (Human-in-the-Loop)

            self.answers_received = False 
            self.latest_answers = {}       

            self.status = "WAITING_FOR_USER"     

            # This waits until submit_answers_signal is called
            await workflow.wait_condition(lambda: self.answers_received)

            # C. Process Answers & Inject Tags
            layer_answers_for_db = {}

            for q_id, answer_val in self.latest_answers.items():
                # Find the question definition to get tag logic
                question_def = next((q for q in self.current_questions if q['node_id'] == q_id), None)
                if question_def:
                    # Logic: Find the selected option to grab new tags
                    # Note: Adjust logic if answer_val is a list (multi-select)
                    selected_opt = next((o for o in question_def['options'] if o['value'] == answer_val), None)
                    
                    if selected_opt:
                        # Inject Tags
                        new_tags = selected_opt.get('tags_injected', [])
                        if new_tags:
                            self.current_tags.extend(new_tags)
                        
                        # Add to Config Payload Accumulator
                        impact = selected_opt.get('payload_impact', {})
                        if impact:
                            self.config_accumulator[q_id] = impact

                        # Prepare for DB Save (Map Question ID -> Answer)
                        layer_answers_for_db[q_id] = answer_val

            # D. Save Progress to DB (Saves individual answers)
            # This calls the activity we defined to INSERT into project_answers
            await workflow.execute_activity(
                "save_config_progress",
                args=[self.project_id, layer_answers_for_db, self.config_accumulator],
                start_to_close_timeout=timedelta(seconds=10)
            )

        # 3. AI Generation (Grand Finale)
        self.status = "GENERATING_CONFIG"
        
        # This calls the AI Agent to process all accumulated impacts into one JSON
        final_config = await workflow.execute_activity(
            "generate_processed_config",
            args=[self.project_id, self.current_tags, self.config_accumulator],
            start_to_close_timeout=timedelta(minutes=1)
        )

        # 🔴 4. Save Final Config to DB (New Step)
        # This ensures the AI's output is stored in project_answers before applying
        await workflow.execute_activity(
            "save_final_config_db",
            args=[self.project_id, final_config],
            start_to_close_timeout=timedelta(seconds=10)
        )

        # 5. Apply Final Config (Deploy to container)
        self.status = "APPLYING_CONFIG"
        await workflow.execute_activity(
            "apply_final_config",
            args=[container_id, final_config],
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        self.status = "COMPLETED"
        return final_config