from temporalio import activity
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text, func, update
from shared.database.db import AsyncSessionLocal as async_session
from shared.models.node_bank import NodeBank
from shared.models.project_answers import ProjectAnswer
from shared.models.core import Project, ProjectStatus
from typing import List, Dict, Any
from containers.ERPNext.config.ai_service import generate_final_config_json
from temporalio.client import Client


# --- NEW ACTIVITY: FETCH CONTEXT TAGS ---
@activity.defn
async def fetch_context_tags(project_id: str) -> List[str]:
    """
    Fetches the context_tags stored in the projects table for initial logic.
    """
    async with async_session() as session:
        # Query Project by the specific ID we passed into the workflow
        stmt = select(Project).where(Project.id == project_id)
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            activity.logger.error(f"❌ Project {project_id} not found!")
            return []
            
        # Extract the tags from the new column
        tags = project.context_tags if project.context_tags else []
        print(f"📡 Activity: Fetched context_tags from DB: {tags}")
        return tags
                
# --- ACTIVITY 1: FETCH QUESTIONS ---
@activity.defn
async def fetch_layer_questions(layer: int, current_tags: List[str], module_ref: str = "ERPNext_Stock") -> List[Dict]:
    """
    Asynchronously fetches questions from Postgres using the 'layer' column.
    """
    async with async_session() as db:
        print(f"Activity: Fetching Layer {layer} for tags {current_tags}")
        
        stmt = select(NodeBank).where(
            NodeBank.module_ref == module_ref,
            NodeBank.layer == layer,
            NodeBank.is_active == True
        )
        result = await db.execute(stmt)
        raw_nodes = result.scalars().all()

        valid_questions = []
        user_tags_set = set(current_tags)

        for node in raw_nodes:
            payload = node.node_data
            logic = payload.get('logic_gates', {})
            required = set(logic.get('required_tags', []))
            excluded = set(logic.get('excluded_tags', []))

            # DEBUG LOGGING (Add this!)
            print(f"🧐 Checking Q: {node.node_id}")
            print(f"   - User Tags: {user_tags_set}")
            print(f"   - Required:  {required}")

            # GATE 1: Exclusions
            if not user_tags_set.isdisjoint(excluded):
                continue 
            
            # GATE 2: Requirements
            if required and user_tags_set.isdisjoint(required):
                continue

            print(f"   ✅ ACCEPTED")

            valid_questions.append({
                "node_id": node.node_id,
                "title": payload['title'],
                "question": payload['content']['question_text'],
                "ui_type": payload['content']['ui_type'],
                "options": payload['options']
            })
            
        return valid_questions

# --- ACTIVITY 2: SAVE ANSWERS (PROGRESS) ---
@activity.defn
async def save_config_progress(project_id: str, layer_answers: dict, accumulator: dict) -> bool:
    """
    Saves individual user answers and their impact to the 'project_answers' table.
    """
    if not layer_answers:
        return True
        
    print(f"💾 SAVING: {len(layer_answers)} answers for Project {project_id}")

    async with async_session() as session:
        async with session.begin():
            for node_id, answer_val in layer_answers.items():
                # Get the impact/tags for this specific question from the accumulator
                impact_data = accumulator.get(node_id, {})
                
                # Construct the UPSERT statement
                stmt = insert(ProjectAnswer).values(
                    project_id=project_id,
                    node_id=node_id,
                    answer_value=answer_val,
                    payload_impact=impact_data,
                    user_role="Config_Agent"
                )
                
                # If collision on (project_id, node_id), update the answer
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_project_node', # Ensure this matches your DB constraint name
                    set_={
                        "answer_value": stmt.excluded.answer_value,
                        "payload_impact": stmt.excluded.payload_impact,
                        "updated_at": func.now() # <--- This works now because we imported func
                    }
                )
                
                await session.execute(stmt)
        
    print("✅ Save complete.")
    return True

# --- ACTIVITY 3: GENERATE AI CONFIG ---
@activity.defn
async def generate_processed_config(project_id: str, tags: list, answers: dict):
    print(f"🧠 GEMINI AGENT: Generating Final Config for Project {project_id}...")
    
    # 1. Generate JSON via AI (This calls your ai_service.py)
    final_json = await generate_final_config_json(tags, answers)
    
    return final_json

# --- ACTIVITY 4: SAVE FINAL CONFIG & UPDATE STATUS ---
@activity.defn
async def save_final_config_db(project_id: str, final_config: dict) -> bool:
    """
    Updates the 'projects' table with the final AI-generated configuration.
    AND sets the status to CONFIG_COMPLETED.
    """
    activity.logger.info(f"🤖 Saving Final Config to PROJECTS table for ID: {project_id}")

    async with async_session() as session:
        async with session.begin():
            # Construct the Update Statement
            stmt = (
                update(Project)
                .where(Project.id == project_id)
                .values(
                    processed_config=final_config,
                    # 🔴 CRITICAL UPDATE: Change status to 'config_completed'
                    status=ProjectStatus.CONFIG_COMPLETED,
                    updated_at=func.now()
                )
            )
            
            result = await session.execute(stmt)
            
            if result.rowcount == 0:
                activity.logger.error(f"❌ Project {project_id} not found!")
                raise ValueError("Project ID not found in database")

    activity.logger.info("✅ Final Config Saved & Project Status Updated to CONFIG_COMPLETED.")
    return True

